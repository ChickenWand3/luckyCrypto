import os
import traceback
import logging
from web3 import Web3
from dotenv import load_dotenv
from funcs import get_wallets
from pycoingecko import CoinGeckoAPI
import time

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

# Load environment variables
load_dotenv()
INFURA_API_KEY = os.getenv("INFURA_API_KEY")
KRAKEN_ADDRESS = os.getenv("KRAKEN_ADDRESS")
SHEET_ID = os.getenv("SHEET_ID") # Found in the Google Sheet URL: https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit
SHEET_NAME = os.getenv("SHEET_NAME")  # Name of the worksheet in your Google Sheet


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
            transaction_data.get("amount", ""),
            transaction_data.get("gasUSD", ""),
        ]

        # Append the row to the Google Sheet
        worksheet.append_row(row)
        logging.info("Transaction logged successfully!")

    except Exception as e:
        logging.info(f"Error logging transaction: {e}")

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
cg = CoinGeckoAPI()
USDC_CONTRACT = web3.eth.contract(address=web3.to_checksum_address(USDC_CONTRACT_ADDRESS), abi=USDC_ABI)
MASTER_WALLET_ADDRESS = web3.to_checksum_address(KRAKEN_ADDRESS)

def convertEthToUSD(balance_eth):
    """Get the ETH balance of an address in USD."""
    try:
        eth_price_data = cg.get_price(ids='ethereum', vs_currencies='usd')
        eth_price_usd = eth_price_data['ethereum']['usd']
        balance_usd = float(balance_eth) * eth_price_usd

        return balance_usd
    except Exception as e:
        logging.error(f"Error getting balance for USD of {balance_eth} ETH: {str(e)}")
        return 0.0

def get_balance(address):
    return USDC_CONTRACT.functions.balanceOf(address).call()

def get_nonce(address):
    return web3.eth.get_transaction_count(address, 'latest')

def estimate_gas(address, balance): #, nonce
    return USDC_CONTRACT.functions.transfer(MASTER_WALLET_ADDRESS, balance).estimate_gas({"from": address})
    

def build_transaction(address, nonce, gas, balance, attempt):
    try:
        gas_price = web3.eth.gas_price
        logging.info(f"Current gas price (wei): {gas_price}")
        # Use a multiplier for gas price to account for network fluctuations
        adjusted_gas_price = int(gas_price * 1.1 * (1 + attempt * 0.4))  # Increase gas price with each attempt 20%
        logging.info(f"Adjusted gas price for attempt {attempt}: {adjusted_gas_price}")
        total_gas_cost_eth = web3.from_wei(gas * adjusted_gas_price, 'ether')

        logging.info(f"Building transaction for {address} with balance {balance} USDC, gas: {gas}, adjusted gas price: {adjusted_gas_price}, total cost in ETH: {total_gas_cost_eth}")

        #Check eth
        address = web3.to_checksum_address(address)
        balance_wei = web3.eth.get_balance(address)
        eth_balance_eth = web3.from_wei(balance_wei, 'ether')


        if eth_balance_eth < total_gas_cost_eth:
            logging.warning(f"Insufficient ETH for gas in wallet {address}. Required: {total_gas_cost_eth} ETH, Available: {eth_balance_eth} ETH")
            return None
        else:
            logging.info(f"Wallet {address} has sufficient ETH for gas: {eth_balance_eth} ETH")

        return USDC_CONTRACT.functions.transfer(MASTER_WALLET_ADDRESS, balance).build_transaction(
            {
                "chainId": 1,
                "gas": int(gas * 1.2),  # 20% buffer for gas limit
                "gasPrice": adjusted_gas_price,
                "nonce": nonce
            })
    except Exception as e:
        logging.error(f"Error building transaction for {address}: {str(e)}")
        raise

def sign_transaction(tx, private_key):
    return web3.eth.account.sign_transaction(tx, private_key)

def send_transaction(signed_tx):
    return web3.eth.send_raw_transaction(signed_tx.raw_transaction)

def wait_for_receipt(tx_hash):
    return web3.eth.wait_for_transaction_receipt(tx_hash, 120)
# Core transfer logic
def transfer_usdc(wallet, max_attempts=3):
    try:
        address = web3.to_checksum_address(wallet["address"])
        balance = get_balance(address)

        if balance == 0:
            logging.info(f"No USDC in wallet {address}")
            return
        balance_usdc = balance / 10**6  # Convert to USDC (6 decimals)
        logging.info(f"Wallet {address} has {balance_usdc:.6f} USDC")

        if balance_usdc < 8.0:  # Minimum transfer amount
            logging.info(f"Skipping transfer for {address} due to low balance: {balance_usdc:.6f} USDC")
            return
        nonce = get_nonce(address)
        gas_estimate = estimate_gas(address, balance) #, nonce
        for attempt in range(max_attempts):
            try:
                time.sleep(1)
                tx = build_transaction(address, nonce, gas_estimate, balance, attempt)
                if not tx:
                    logging.error(f"Failed to build transaction for {address}. Insufficient ETH for gas.")
                    return
                signed_tx = sign_transaction(tx, wallet["private_key"])
                time.sleep(1)  # Wait a bit before sending to avoid nonce issues
                tx_hash = send_transaction(signed_tx)
                time.sleep(1)  # Wait a bit before checking receipt should fix the failed transaction but actually went through
                receipt = wait_for_receipt(tx_hash)
                if receipt["status"] == 1:
                    logging.info(f"Transferred {balance_usdc:.6f} USDC from {address} to {MASTER_WALLET_ADDRESS}. Tx: {tx_hash.hex()}")
                    #'''
                    log_transaction({
                    "recipient": wallet.get("name", "Unknown"),
                    "email": wallet.get("email", "Unknown"),
                    "address": address,
                    "amount": balance_usdc,
                    "gasUSD": convertEthToUSD(receipt['gasUsed'] * receipt['effectiveGasPrice'] / 10**18)  # Convert gas cost to USD
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
                time.sleep(2 ** attempt)
    except Exception as e:
        logging.error(f"Error processing wallet {wallet.get('address', 'unknown')}: {str(e)}")
        logging.error(traceback.format_exc())

def main():
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

    for wallet in valid_wallets:
        transfer_usdc(wallet)
    logging.info("USDC sweep completed")
    return True

if __name__ == "__main__":
    logging.info("Starting USDC sweep script")
    result = main()
