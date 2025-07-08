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


# This script sweeps USDC from many individual wallets to a master wallet.
# To be ran at 12:00 midnight PST every day using a cron job

# Load environment variables
load_dotenv()
INFURA_API_KEY = os.getenv("INFURA_API_KEY")
MASTER_PRIVATE_KEY = os.getenv("MASTER_PRIVATE_KEY")
MASTER_WALLET_ADDRESS = Account.from_key(MASTER_PRIVATE_KEY).address if MASTER_PRIVATE_KEY else None

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
USDC_CONTRACT = web3.eth.contract(address=USDC_CONTRACT_ADDRESS, abi=USDC_ABI)

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
        executor, web3.eth.get_transaction_count, address
    )

async def estimate_gas(address, balance):
    return await asyncio.get_event_loop().run_in_executor(
        executor,
        USDC_CONTRACT.functions.transfer(MASTER_WALLET_ADDRESS, balance).estimate_gas,
        {"from": address}
    )

async def build_transaction(address, nonce, gas, balance):
    return await asyncio.get_event_loop().run_in_executor(
        executor,
        USDC_CONTRACT.functions.transfer(MASTER_WALLET_ADDRESS, balance).build_transaction,
        {
            "chainId": 1,
            "gas": int(gas * 1.2),
            "gasPrice": web3.eth.gas_price,
            "nonce": nonce
        }
    )

async def sign_transaction(tx, private_key):
    return await asyncio.get_event_loop().run_in_executor(
        executor, web3.eth.account.sign_transaction, tx, private_key
    )

async def send_transaction(signed_tx):
    return await asyncio.get_event_loop().run_in_executor(
        executor, web3.eth.send_raw_transaction, signed_tx.rawTransaction
    )

async def wait_for_receipt(tx_hash):
    return await asyncio.get_event_loop().run_in_executor(
        executor, web3.eth.wait_for_transaction_receipt, tx_hash, 120
    )

# Core transfer logic
async def transfer_usdc(wallet, max_attempts=3):
    # Limit concurrent transfers
    async with semaphore:
        try:
            balance = await get_balance(wallet["address"])
            if balance == 0:
                logging.info(f"No USDC in wallet {wallet['address']}")
                return

            nonce = await get_nonce(wallet["address"]) # Get nonce for wallet transaction for this transfer
            gas_estimate = await estimate_gas(wallet["address"], balance) # Get gas estimate for the transfer
            tx = await build_transaction(wallet["address"], nonce, gas_estimate, balance) # Build the transaction

            for attempt in range(max_attempts):
                try:
                    signed_tx = await sign_transaction(tx, wallet["private_key"]) # Sign the transaction with the wallet's private key
                    tx_hash = await send_transaction(signed_tx) # Send the signed transaction to the network
                    receipt = await wait_for_receipt(tx_hash) # Wait for the transaction receipt 

                    if receipt["status"] == 1: # Validate the transaction was successful
                        logging.info(f"Transferred {balance / 10**6} USDC from {wallet['address']} to {MASTER_WALLET_ADDRESS}. Tx: {tx_hash.hex()}")
                        return
                    else: # Log an error if the transaction failed
                        logging.error(f"Transaction failed for {wallet['address']}. Tx: {tx_hash.hex()}")
                        return
                except Exception as e: # Handle any exceptions during the transfer process
                    if attempt == max_attempts - 1:
                        logging.error(f"Failed to transfer from {wallet['address']} after {max_attempts} attempts: {str(e)}")
                        return
                    # Retry with exponential backoff
                    logging.warning(f"Retrying transfer for {wallet['address']} (attempt {attempt + 1}) due to error: {str(e)}")
                    await asyncio.sleep(2 ** attempt)
        except Exception as e: # Handle general exceptions
            logging.error(f"Error processing wallet {wallet['address']}: {str(e)}")
            logging.error(traceback.format_exc())

# Use get_wallets func to gather wallets
    logging.info("Gathering wallets")
    logging.info(f"Gathered wallets")
    return None

# Runner
async def main():
    # Gather all wallets
    wallets = get_wallets()
    if not wallets:
        logging.error("No wallets found. Exiting.")
        return
    # Create tasks and run them concurrently
    tasks = [transfer_usdc(wallet) for wallet in wallets]
    await asyncio.gather(*tasks)
    return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())



# Optional improvement later down the road:
    # Asyncio queue - might only be useful for a larger number of wallets