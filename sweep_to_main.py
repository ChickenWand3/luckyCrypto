import os
import json
import traceback
import asyncio
import logging
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from funcs import get_wallets, verifyUserData

import gspread
from google.oauth2.service_account import Credentials
import datetime


# This script sweeps USDC from many individual wallets to a master wallet.
# To be ran at 12:00 midnight PST every day using a cron job

# Set up logging
logging.basicConfig(filename='usdc_transfer.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')


# Define the scope and load credentials
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
CREDS_FILE = "credentials.json"
SHEET_ID = "1UjPoBYo40jJEtRU8wkZxeawonxccuXjypuR0-Iayr4o"  # Found in the Google Sheet URL: https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit
SHEET_NAME = "Transactions"  # Name of the worksheet in your Google Sheet

def log_transaction(transaction_data):
    try:
        # Authenticate with Google Sheets API
        creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
        client = gspread.authorize(creds)

        # Open the Google Sheet
        spreadsheet = client.open_by_key(SHEET_ID)
        worksheet = spreadsheet.worksheet(SHEET_NAME)

        # Prepare transaction data (example format)
        # Assuming transaction_data is a dict like: {"amount": 100.50, "recipient": "John Doe", "status": "Success"}
        row = [
            datetime.datetime.now().isoformat(),  # Timestamp
            transaction_data.get("recipient", ""),
            transaction_data.get("email", ""),
            transaction_data.get("address", ""),
            transaction_data.get("amount", "")
        ]

        # Append the row to the Google Sheet
        worksheet.append_row(row)
        print("Transaction logged successfully!")

    except Exception as e:
        print(f"Error logging transaction: {e}")

# Load environment variables
load_dotenv()
INFURA_API_KEY = os.getenv("INFURA_API_KEY")
KRAKEN_ADDRESS = os.getenv("KRAKEN_ADDRESS")

# Ethereum configuration
MAINNET_RPC_URL = f"https://mainnet.infura.io/v3/{INFURA_API_KEY}"
USDC_CONTRACT_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
USDC_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
]



# Setup Web3 and Contract
web3 = Web3(Web3.HTTPProvider(MAINNET_RPC_URL))
USDC_CONTRACT = web3.eth.contract(address=web3.to_checksum_address(USDC_CONTRACT_ADDRESS), abi=USDC_ABI)
MASTER_WALLET_ADDRESS = web3.to_checksum_address(KRAKEN_ADDRESS)

# Thread pool and concurrency control
MAX_THREADS = 8
executor = ThreadPoolExecutor(max_workers=MAX_THREADS)
semaphore = asyncio.Semaphore(8)  # Limit number of concurrent transfers

# Async wrappers for blocking Web3 operations
async def get_balance(address):
    return await asyncio.get_event_loop().run_in_executor(
        executor, USDC_CONTRACT.functions.balanceOf(address).call
    )

async def get_nonce(address):
    return await asyncio.get_event_loop().run_in_executor(
        executor, web3.eth.get_transaction_count, address, 'pending'
    )

async def estimate_gas(address, balance):
    return await asyncio.get_event_loop().run_in_executor(
        executor,
        USDC_CONTRACT.functions.transfer(MASTER_WALLET_ADDRESS, balance).estimate_gas,
        {"from": address}
    )

async def build_transaction(address, nonce, gas, balance):
    try:
        gas_price = web3.eth.gas_price
        # Use a multiplier for gas price to account for network fluctuations
        adjusted_gas_price = int(gas_price * 1.2)
        return await asyncio.get_event_loop().run_in_executor(
            executor,
            USDC_CONTRACT.functions.transfer(MASTER_WALLET_ADDRESS, balance).build_transaction,
            {
                "chainId": 1,
                "gas": int(gas * 1.2),  # 20% buffer for gas limit
                "gasPrice": adjusted_gas_price,
                "nonce": nonce
            }
        )
    except Exception as e:
        logging.error(f"Error building transaction for {address}: {str(e)}")
        raise

async def sign_transaction(tx, private_key):
    return await asyncio.get_event_loop().run_in_executor(
        executor, web3.eth.account.sign_transaction, tx, private_key
    )

async def send_transaction(signed_tx):
    return await asyncio.get_event_loop().run_in_executor(
        executor, web3.eth.send_raw_transaction, signed_tx.raw_transaction
    )

async def wait_for_receipt(tx_hash):
    return await asyncio.get_event_loop().run_in_executor(
        executor, web3.eth.wait_for_transaction_receipt, tx_hash, 120
    )

# Core transfer logic
async def transfer_usdc(wallet, max_attempts=3):
    async with semaphore:
        try:
            # Validate wallet data
            #if not verifyUserData(wallet):
            #    logging.error(f"Invalid wallet data for {wallet.get('address', 'unknown')}")
            #    return
            #print(1)
            address = web3.to_checksum_address(wallet["address"])
            balance = await get_balance(address)
            if balance == 0:
                logging.info(f"No USDC in wallet {address}")
                return
            #print(2)
            balance_usdc = balance / 10**6  # Convert to USDC (6 decimals)
            logging.info(f"Wallet {address} has {balance_usdc:.6f} USDC")

            if balance_usdc < 8.0:  # Minimum transfer amount
                logging.info(f"Skipping transfer for {address} due to low balance: {balance_usdc:.6f} USDC")
                return
            #print(3)
            nonce = await get_nonce(address)
            gas_estimate = await estimate_gas(address, balance)
            tx = await build_transaction(address, nonce, gas_estimate, balance)
            #print(4)
            for attempt in range(max_attempts):
                try:
                    signed_tx = await sign_transaction(tx, wallet["private_key"])
                    tx_hash = await send_transaction(signed_tx)
                    receipt = await wait_for_receipt(tx_hash)
                    #print(5)
                    if receipt["status"] == 1:
                        logging.info(f"Transferred {balance_usdc:.6f} USDC from {address} to {MASTER_WALLET_ADDRESS}. Tx: {tx_hash.hex()}")
                        #'''
                        log_transaction({
                        "recipient": wallet.get("name", "Unknown"),
                        "email": wallet.get("email", "Unknown"),
                        "address": address,
                        "amount": balance_usdc
                        })
                        #'''
                        return
                    else:
                        logging.error(f"Transaction failed for {address}. Tx: {tx_hash.hex()}")
                        return
                except Exception as e:
                    if attempt == max_attempts - 1:
                        logging.error(f"Failed to transfer from {address} after {max_attempts} attempts: {str(e)}")
                        return
                    logging.warning(f"Retrying transfer for {address} (attempt {attempt + 1}) due to error: {str(e)}")
                    await asyncio.sleep(2 ** attempt)
        except Exception as e:
            logging.error(f"Error processing wallet {wallet.get('address', 'unknown')}: {str(e)}")
            logging.error(traceback.format_exc())

async def main():
    # Check Web3 connectivity
    if not web3.is_connected():
        logging.error("Failed to connect to Ethereum network via Infura")
        return False

    # Gather and validate wallets
    logging.info("Gathering wallets")
    wallets = get_wallets()
    if not wallets:
        logging.error("No wallets found. Exiting.")
        return False

    # Filter enabled and valid wallets
    valid_wallets = [w for w in wallets if w.get("enabled", False)]
    logging.info(f"Found {len(valid_wallets)} valid and enabled wallets")

    # Create tasks and run them concurrently
    tasks = [transfer_usdc(wallet) for wallet in valid_wallets]
    await asyncio.gather(*tasks)
    logging.info("USDC sweep completed")
    return True

if __name__ == "__main__":
    logging.info("Starting USDC sweep script")
    asyncio.run(main())



# Optional improvement later down the road:
    # Asyncio queue - might only be useful for a larger number of wallets