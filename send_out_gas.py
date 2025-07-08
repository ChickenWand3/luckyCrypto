

# This script send ETH to many individual wallets if they are running low on gas.
# To be ran at 11:30 PST every day using a cron job

#wallets = get_wallets()
# for wallet in wallets:
#     if wallet["enabled"]:
#         if needGas(wallet):  # Check if balance is less than 0.01 ETH
#             send_gas(wallet["address"], 0.01)  # Send 0.01 ETH to the wallet









import os
import json
import logging
from web3 import Web3
from eth_account import Account
from cryptography.fernet import Fernet
from pycoingecko import CoinGeckoAPI
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(filename='usdc_transfer.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()
INFURA_API_KEY = os.getenv('INFURA_API_KEY')
MAINNET_RPC_URL = f"https://mainnet.infura.io/v3/{INFURA_API_KEY}"

# Initialize web3 and CoinGecko
web3 = Web3(Web3.HTTPProvider(MAINNET_RPC_URL))
cg = CoinGeckoAPI()

def needGas(wallet):
    try:
        # Get ETH balance
        address = web3.to_checksum_address(wallet['address'])
        balance_wei = web3.eth.get_balance(address)
        balance_eth = web3.from_wei(balance_wei, 'ether')

        # Get ETH price in USD
        eth_price_data = cg.get_price(ids='ethereum', vs_currencies='usd')
        eth_price_usd = eth_price_data['ethereum']['usd']

        # Calculate balance in USD
        balance_usd = balance_eth * eth_price_usd

        # Check if balance is less than $5
        is_below_5_usd = balance_usd < 5.0
        logging.info(f"Wallet {address}: {balance_eth:.6f} ETH (${balance_usd:.2f}), Below $5: {is_below_5_usd}")
        return is_below_5_usd

    except Exception as e:
        logging.error(f"Error checking balance for {wallet['address']}: {str(e)}")
        return False 