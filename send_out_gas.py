import os
import json
import logging
import time
import krakenex
from web3 import Web3
from pycoingecko import CoinGeckoAPI
from dotenv import load_dotenv
from funcs import get_wallets

# Set up logging
logging.basicConfig(filename='usdc_transfer.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()
INFURA_API_KEY = os.getenv('INFURA_API_KEY')
KRAKEN_API_KEY = os.getenv('KRAKEN_API_KEY')
KRAKEN_API_SECRET = os.getenv('KRAKEN_API_SECRET')
KRAKEN_ADDRESS = os.getenv('KRAKEN_ADDRESS')

MAINNET_RPC_URL = f"https://mainnet.infura.io/v3/{INFURA_API_KEY}"

# Initialize web3, CoinGecko, and Kraken
web3 = Web3(Web3.HTTPProvider(MAINNET_RPC_URL))
cg = CoinGeckoAPI()
kraken = krakenex.API(key=KRAKEN_API_KEY, secret=KRAKEN_API_SECRET)

def needGas(wallet):
    """Check if wallet balance is less than $5 worth of ETH."""
    try:
        address = web3.to_checksum_address(wallet['address'])
        balance_wei = web3.eth.get_balance(address)
        balance_eth = web3.from_wei(balance_wei, 'ether')

        eth_price_data = cg.get_price(ids='ethereum', vs_currencies='usd')
        eth_price_usd = eth_price_data['ethereum']['usd']

        balance_usd = float(balance_eth) * eth_price_usd
        is_below_5_usd = balance_usd < 5.0
        logging.info(f"Wallet {address}: {balance_eth:.6f} ETH (${balance_usd:.2f}), Below $5: {is_below_5_usd}")
        return is_below_5_usd
    except Exception as e:
        logging.error(f"Error checking balance for {wallet['address']}: {str(e)}")
        return False

def sendGas(to_address, nickname, usd_amount=5.0):
    """Send ETH equivalent to ~$5 USD from Kraken account."""
    try:
        # Get ETH price
        eth_price_data = cg.get_price(ids='ethereum', vs_currencies='usd')
        eth_price_usd = eth_price_data['ethereum']['usd']

        # Calculate ETH amount (~$5)
        eth_amount = usd_amount / eth_price_usd

        # Initiate withdrawal via Kraken API
        withdrawal_info = {
            'asset': 'ETH',
            'key': str(nickname)+"!",  # Withdrawal key name configured in Kraken
            'amount': str(eth_amount),
            'address': str(to_address).lower()
        }

        logging.info(f"Preparing to send {eth_amount:.6f} ETH to {to_address} via Kraken account '{nickname}'")

        # Send withdrawal request
        response = kraken.query_private('Withdraw', withdrawal_info)
        
        if 'error' in response and response['error']:
            logging.error(f"Kraken API error for {to_address}: {response['error']}")
            return False

        logging.info(f"Initiated withdrawal of {eth_amount:.6f} ETH to {to_address}, Ref ID: {response.get('result', {}).get('refid', 'N/A')}")
        return True
    except Exception as e:
        logging.error(f"Error sending ETH to {to_address}: {str(e)}")
        return False

def refillGas():
    """Main function to check and distribute gas to wallets."""
    logging.info("Starting gas distribution script")
    
    if not web3.is_connected():
        logging.error("Failed to connect to Ethereum network")
        return

    wallets = get_wallets()
    for wallet in wallets:
        if wallet.get("enabled", False):
            if needGas(wallet):
                success = sendGas(wallet["address"], wallet["kraken_nickname"], 5.0)
                if success:
                    logging.info(f"Successfully initiated gas transfer to {wallet['address']} - Owner: {wallet['name']} ({wallet['email']})")
                else:
                    logging.error(f"Failed to initiate gas transfer to {wallet['address']}")
                # Avoid rate limiting
                time.sleep(2)

if __name__ == "__main__":
    refillGas()