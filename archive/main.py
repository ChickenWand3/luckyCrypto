import os
import json
import time
import logging
import schedule
from web3 import Web3
from eth_account import Account
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(filename='usdc_transfer.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()
INFURA_API_KEY = os.getenv('INFURA_API_KEY')
MASTER_PRIVATE_KEY = os.getenv('MASTER_PRIVATE_KEY')
MASTER_WALLET_ADDRESS = Account.from_key(MASTER_PRIVATE_KEY).address if MASTER_PRIVATE_KEY else None

# Ethereum mainnet configuration
MAINNET_RPC_URL = f"https://mainnet.infura.io/v3/{INFURA_API_KEY}"
USDC_CONTRACT_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"  # USDC on Ethereum mainnet
USDC_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    }
]

# Connect to Ethereum mainnet
web3 = Web3(Web3.HTTPProvider(MAINNET_RPC_URL))
usdc_contract = web3.eth.contract(address=USDC_CONTRACT_ADDRESS, abi=USDC_ABI)

# Generate or load wallets
def generate_wallets(num_wallets=1, wallets_file="wallets.enc", key_file="encryption_key.txt"):
    if os.path.exists(wallets_file) and os.path.exists(key_file):
        logging.info("Loading existing wallets")
        with open(key_file, "rb") as f:
            key = f.read()
        cipher = Fernet(key)
        with open(wallets_file, "rb") as f:
            encrypted_data = f.read()
        wallets = json.loads(cipher.decrypt(encrypted_data).decode())
        return wallets

    logging.info("Generating new wallets")
    Account.enable_unaudited_hdwallet_features()
    mnemonic = Account.create_with_mnemonic().mnemonic
    wallets = []
    for i in range(num_wallets):
        account = Account.from_mnemonic(mnemonic, account_path=f"m/44'/60'/0'/0/{i}")
        wallets.append({
            "address": account.address,
            "private_key": account.key.hex(),
            "mnemonic": mnemonic
        })

    # Save wallets securely
    key = Fernet.generate_key()
    cipher = Fernet(key)
    with open(wallets_file, "wb") as f:
        f.write(cipher.encrypt(json.dumps(wallets).encode()))
    with open(key_file, "wb") as f:
        f.write(key)
    
    logging.info(f"Generated {num_wallets} wallets. Mnemonic: {mnemonic}. Store mnemonic securely offline!")
    print(f"Generated {num_wallets} wallets. Mnemonic: {mnemonic}")
    print("Store mnemonic securely offline (e.g., paper or encrypted USB). Do not share!")
    return wallets

# Fund wallets with ETH and USDC
def fund_wallets(wallets, eth_amount=0.01, usdc_amount=1000, max_attempts=3):
    logging.info("Funding wallets with ETH and USDC")
    for wallet in wallets:
        for attempt in range(max_attempts):
            try:
                # Fund ETH
                nonce = web3.eth.get_transaction_count(MASTER_WALLET_ADDRESS)
                eth_tx = {
                    'to': wallet['address'],
                    'value': web3.to_wei(eth_amount, 'ether'),
                    'gas': 21000,
                    'gasPrice': web3.to_wei(50, 'gwei'),
                    'nonce': nonce,
                    'chainId': 1
                }
                signed_eth = web3.eth.account.sign_transaction(eth_tx, MASTER_PRIVATE_KEY)
                eth_tx_hash = web3.eth.send_raw_transaction(signed_eth.raw_transaction)
                eth_receipt = web3.eth.wait_for_transaction_receipt(eth_tx_hash, timeout=120)
                if eth_receipt["status"] == 1:
                    logging.info(f"Funded {eth_amount} ETH to {wallet['address']}. Tx: {eth_tx_hash.hex()}")
                else:
                    logging.error(f"ETH funding failed for {wallet['address']}. Tx: {eth_tx_hash.hex()}")
                    continue

                # Fund USDC
                nonce += 1
                usdc_tx = usdc_contract.functions.transfer(wallet['address'], int(usdc_amount * 10**6)).build_transaction({
                    'from': MASTER_WALLET_ADDRESS,
                    'gas': 100000,
                    'gasPrice': web3.to_wei(50, 'gwei'),
                    'nonce': nonce,
                    'chainId': 1
                })
                signed_usdc = web3.eth.account.sign_transaction(usdc_tx, MASTER_PRIVATE_KEY)
                usdc_tx_hash = web3.eth.send_raw_transaction(signed_usdc.raw_transaction)
                usdc_receipt = web3.eth.wait_for_transaction_receipt(usdc_tx_hash, timeout=120)
                if usdc_receipt["status"] == 1:
                    logging.info(f"Funded {usdc_amount} USDC to {wallet['address']}. Tx: {usdc_tx_hash.hex()}")
                    break
                else:
                    logging.error(f"USDC funding failed for {wallet['address']}. Tx: {usdc_tx_hash.hex()}")
            except Exception as e:
                if attempt == max_attempts - 1:
                    logging.error(f"Failed to fund {wallet['address']} after {max_attempts} attempts: {str(e)}")
                time.sleep(2 ** attempt)

# Transfer USDC to master wallet with retry mechanism
def transfer_usdc(wallet, max_attempts=3):
    try:
        balance = usdc_contract.functions.balanceOf(wallet["address"]).call()
        if balance == 0:
            logging.info(f"No USDC in wallet {wallet['address']}")
            return

        nonce = web3.eth.get_transaction_count(wallet["address"])
        gas_estimate = usdc_contract.functions.transfer(MASTER_WALLET_ADDRESS, balance).estimate_gas({"from": wallet["address"]})
        tx = usdc_contract.functions.transfer(MASTER_WALLET_ADDRESS, balance).build_transaction({
            "chainId": 1,  # Ethereum mainnet chain ID
            "gas": int(gas_estimate * 1.2),  # 20% buffer
            "gasPrice": web3.eth.gas_price,
            "nonce": nonce
        })

        for attempt in range(max_attempts):
            try:
                signed_tx = web3.eth.account.sign_transaction(tx, wallet["private_key"])
                tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
                receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                if receipt["status"] == 1:
                    logging.info(f"Transferred {balance / 10**6} USDC from {wallet['address']} to {MASTER_WALLET_ADDRESS}. Tx: {tx_hash.hex()}")
                    return
                else:
                    logging.error(f"Transaction failed for {wallet['address']}. Tx: {tx_hash.hex()}")
                    return
            except Exception as e:
                if attempt == max_attempts - 1:
                    logging.error(f"Failed to transfer from {wallet['address']} after {max_attempts} attempts: {str(e)}")
                    return
                time.sleep(2 ** attempt)  # Exponential backoff

    except Exception as e:
        logging.error(f"Error processing wallet {wallet['address']}: {str(e)}")

# Main transfer function
def transfer_all_usdc():
    logging.info("Starting daily USDC transfer at midnight PST")
    wallets = generate_wallets()
    for wallet in wallets:
        transfer_usdc(wallet)
    logging.info("Completed daily USDC transfer")

# Schedule transfers
def main():
    if not INFURA_API_KEY or not MASTER_PRIVATE_KEY:
        logging.error("Missing INFURA_API_KEY or MASTER_PRIVATE_KEY in .env file")
        raise ValueError("Please set INFURA_API_KEY and MASTER_PRIVATE_KEY in .env file")
    
    if not web3.is_connected():
        logging.error("Failed to connect to Ethereum mainnet")
        raise ConnectionError("Cannot connect to Ethereum mainnet")

    # Generate or load wallets
    wallets = generate_wallets()
    
    # Fund wallets (manual step)
    fund_wallets(wallets)
    
    # Schedule transfers at midnight PST
    schedule.every().day.at("00:00", "America/Los_Angeles").do(transfer_all_usdc)
    
    logging.info("Starting transfer schedule")
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"Script failed: {str(e)}")