import os
import json
import logging
from web3 import Web3
from eth_account import Account
from cryptography.fernet import Fernet
from dotenv import load_dotenv



def verifyUserData(user_data, highest_index, num_wallets):
    # If user_data is not provided, create placeholder name/email pairs
    if user_data is None:
        user_data = [{"name": f"User{highest_index+i+1}", "email": f"user{highest_index+i+1}@example.com"} for i in range(num_wallets)]
    else:
        # Ensure user_data length matches num_wallets
        if len(user_data) != num_wallets:
            raise ValueError(f"Provided user_data length ({len(user_data)}) does not match num_wallets ({num_wallets})")
        # Validate user_data entries
        for data in user_data:
            if not isinstance(data, dict) or "name" not in data or "email" not in data:
                raise ValueError("Each user_data entry must be a dict with 'name' and 'email' keys")
    return user_data

# Generate wallets with mnemonic and user data
def generate_wallets(num_wallets=1, wallets_file="wallets.enc", key_file="encryption_key.txt", user_data=None):
    logging.info("Generating wallets...")

    if wallets_file == "masterWallets.enc":
        logging.info("Generating master wallets...")
        if os.path.exists(wallets_file) and os.path.exists(key_file):
            logging.error("Master wallet already exists. Stopping override.")
            return False

    # Check if wallets file and key file exist
    if os.path.exists(wallets_file) and os.path.exists(key_file):
        logging.info("Loading existing wallets")
        with open(key_file, "rb") as f:
            key = f.read()
        cipher = Fernet(key)
        with open(wallets_file, "rb") as f:
            encrypted_data = f.read()
        data = json.loads(cipher.decrypt(encrypted_data).decode())
        wallets = data["wallets"]
        mnemonic = data["metadata"]["mnemonic"]
        highest_index = len(wallets) - 1
        user_data = verifyUserData(user_data, highest_index+1, num_wallets)
        
        # Generate new wallets with incremented address_index
        logging.info(f"Appending {num_wallets} new wallets starting at address_index {highest_index + 1}")
        Account.enable_unaudited_hdwallet_features()
        new_wallets = []
        for i in range(num_wallets):
            account = Account.from_mnemonic(mnemonic, account_path=f"m/44'/60'/0'/0/{highest_index + 1 + i}")
            new_wallets.append({
                "address": account.address,
                "private_key": account.key.hex(),
                "mnemonic": mnemonic,
                "name": user_data[i]["name"],
                "email": user_data[i]["email"],
                "kraken_nickname": f"Wallet#{highest_index + 1 + i}",
                "enabled": True
            })
            logging.info(f"Generated new wallet with address_index {highest_index + 1 + i}: {account.address}")
        
        # Append new wallets to existing list
        wallets.extend(new_wallets)
        # Create JSON structure with metadata
        data = {
            "metadata": {
                "mnemonic": mnemonic
            },
            "wallets": wallets
        }

        # Save wallets securely
        key = Fernet.generate_key()
        cipher = Fernet(key)
        with open(wallets_file, "wb") as f:
            f.write(cipher.encrypt(json.dumps(data).encode()))
        with open(key_file, "wb") as f:
            f.write(key)
        return True
    else:
        # Generate new wallets and mnemonic
        logging.info("Generating new wallets")
        Account.enable_unaudited_hdwallet_features()
        acct, mnemonic = Account.create_with_mnemonic() #Tuple so getting mnemonic
        wallets = []
        user_data = verifyUserData(user_data, 0, num_wallets)
        logging.info(f"Generated mnemonic: {mnemonic}")
        for i in range(num_wallets):
            account = Account.from_mnemonic(mnemonic, account_path=f"m/44'/60'/0'/0/{i}")
            wallets.append({
                "address": account.address,
                "private_key": account.key.hex(),
                "mnemonic": mnemonic,
                "name": user_data[i]["name"],
                "email": user_data[i]["email"],
                "kraken_nickname": f"Wallet#{i}",
                "enabled": True
            })

            logging.info(f"Generated wallet with address_index {i}: {account.address}")
        
        # Create JSON structure with metadata
        data = {
            "metadata": {
                "mnemonic": mnemonic
            },
            "wallets": wallets
        }

        # Save wallets securely
        key = Fernet.generate_key()
        cipher = Fernet(key)
        with open(wallets_file, "wb") as f:
            f.write(cipher.encrypt(json.dumps(data).encode()))
        with open(key_file, "wb") as f:
            f.write(key)
        return True


def get_wallets(wallets_file="wallets.enc", key_file="encryption_key.txt"):
    if not os.path.exists(wallets_file) or not os.path.exists(key_file):
        logging.error("Wallets file or key file does not exist")
        return []
    with open(key_file, "rb") as f:
        key = f.read()
    cipher = Fernet(key)
    with open(wallets_file, "rb") as f:
        encrypted_data = f.read()
    data = json.loads(cipher.decrypt(encrypted_data).decode())
    wallets = data["wallets"]
    logging.info(f"Loaded {len(wallets)} wallets from file")
    return wallets

def getUSDC(wallet_address, usdc_contract, web3):
    """Get USDC balance for a given wallet address."""
    try:
        address = web3.to_checksum_address(wallet_address)
        balance_wei = usdc_contract.functions.balanceOf(address).call()
        balance_usdc = balance_wei / 10**6
        return balance_usdc
    except Exception as e:
        logging.error(f"Error getting USDC balance for {wallet_address}: {str(e)}")
        return 0.0
    
def getUSDCContractAndWeb3():
    # Load environment variables
    load_dotenv()
    INFURA_API_KEY = os.getenv('INFURA_API_KEY')
    
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
    
    if not web3.is_connected():
        logging.error("Failed to connect to Ethereum mainnet")
        raise ConnectionError("Cannot connect to Ethereum mainnet")
    
    return usdc_contract, web3

def jsonify_walletBalances(wallets_file="wallets.enc", key_file="encryption_key.txt", wallets=None):
    if not wallets:
        logging.info("No wallets found")
        return {"wallets": []}
    
    usdc_contract, web3 = getUSDCContractAndWeb3()
    
    message = {"wallets": []}
    for wallet in wallets:
        message["wallets"].append({
            "name": wallet["name"],
            "USDC": getUSDC(wallet["address"], usdc_contract, web3),
            "ETH": web3.from_wei(web3.eth.get_balance(wallet["address"]), 'ether'),
            "Address": wallet["address"],
        })
    return message
    

def search_wallets(wallet_name, wallet_email, wallets_file="wallets.enc", key_file="encryption_key.txt"):
    wallets = get_wallets(wallets_file, key_file)
    results = []
    for wallet in wallets:
        if (wallet_name and wallet["name"] == wallet_name) or (wallet_email and wallet["email"] == wallet_email):
            results.append(wallet)
    if results:
        logging.info(f"Found {len(results)} wallets matching search criteria")
    else:
        logging.info("No wallets found matching search criteria")
    return results

def transfer_usdc_if_above_one(wallet_address, private_key):
    """Transfer USDC to Kraken wallet if balance > $1 and enough ETH for gas."""
    # Load environment variables
    load_dotenv()
    KRAKEN_ADDRESS = os.getenv('KRAKEN_ADDRESS')
    INFURA_API_KEY = os.getenv('INFURA_API_KEY')
    if not KRAKEN_ADDRESS or not INFURA_API_KEY:
        logging.error("Kraken address or Infura API key not set in environment variables")
        return False
    
    usdc_contract, web3 = getUSDCContractAndWeb3()  # Need to send USDC

    try:
        # Convert addresses to checksum format
        address = web3.to_checksum_address(wallet_address)
        kraken_address = web3.to_checksum_address(KRAKEN_ADDRESS)

        # Get USDC balance (USDC has 6 decimals)
        usdc_balance = usdc_contract.functions.balanceOf(address).call()
        usdc_balance_decimal = usdc_balance / 10**6  # Convert to human-readable USDC

        # Check if USDC balance is worth more than $1 (assuming 1 USDC ≈ $1)
        if usdc_balance_decimal < 1:
            logging.info(f"USDC balance ({usdc_balance_decimal}) is less than $1, skipping transfer")
            return True

        # Estimate gas for USDC transfer
        usdc_transfer_tx = usdc_contract.functions.transfer(
            kraken_address,
            usdc_balance
        ).build_transaction({
            'from': address,
            'nonce': web3.eth.get_transaction_count(address),
            'gasPrice': web3.eth.gas_price
        })
        gas_estimate = web3.eth.estimate_gas(usdc_transfer_tx)
        gas_estimate_buffered = int(gas_estimate * 1.15)  # Increase gas estimate by 15%
        gas_price = web3.eth.gas_price  # Current gas price in wei
        gas_cost_wei = gas_estimate_buffered * gas_price  # Use buffered gas for cost
        gas_cost_eth = web3.from_wei(gas_cost_wei, 'ether')

        # Get ETH balance
        eth_balance = web3.eth.get_balance(address)
        eth_balance_decimal = web3.from_wei(eth_balance, 'ether')

        # Check if enough ETH for gas with buffer
        if eth_balance < gas_cost_wei:
            logging.error(f"Insufficient ETH for gas: {eth_balance_decimal} ETH available, {gas_cost_eth} ETH needed (with 15% buffer)")
            return False

        # Build and sign USDC transfer transaction with buffered gas
        usdc_transfer_tx['gas'] = gas_estimate_buffered  # Use buffered gas for transaction
        signed_tx = web3.eth.account.sign_transaction(usdc_transfer_tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        logging.info(f"USDC transfer sent: {tx_hash.hex()}")

        # Wait for transaction confirmation
        web3.eth.wait_for_transaction_receipt(tx_hash)
        return True

    except Exception as e:
        logging.error(f"Error during USDC transfer: {e}")
        return False

def disable_wallet(wallet_email, wallet_name, wallets_file="wallets.enc", key_file="encryption_key.txt"):
    wallets = get_wallets(wallets_file, key_file)
    for wallet in wallets:
        if (wallet["email"] == wallet_email or wallet["name"] == wallet_name) and wallet.get("enabled", True):

            if transfer_usdc_if_above_one(wallet["address"], wallet["private_key"]):
                logging.info(f"Transferred USDC from {wallet['address']} to master wallet before disabling")
            
            wallet["enabled"] = False
            logging.info(f"Disabled wallet for email: {wallet_email}")

            # Save wallets securely
            data = {
                "metadata": {
                    "mnemonic": wallet["mnemonic"]
                },
                "wallets": wallets
            }
            key = Fernet.generate_key()
            cipher = Fernet(key)
            with open(wallets_file, "wb") as f:
                f.write(cipher.encrypt(json.dumps(data).encode()))
            with open(key_file, "wb") as f:
                f.write(key)
            if wallet["name"] == wallet_name:
                logging.info(f"Disabled wallet for name: {wallet_name}")
            elif wallet["email"] == wallet_email:
                logging.info(f"Disabled wallet for email: {wallet_email}")
            return True
    logging.info(f"No valid matching wallet found for email: {wallet_email} or name: {wallet_name}")
    return False #Couldn't find wallet

# Schedule transfers
def main():
    # Set up logging
    logging.basicConfig(filename='usdc_transfer.log', level=logging.INFO, 
                        format='%(asctime)s - %(levelname)s - %(message)s')

    #generate_wallets(num_wallets=1)
    wallets = get_wallets()

    logging.info(jsonify_walletBalances(wallets_file="wallets.enc", key_file="encryption_key.txt", wallets=wallets))



    for wallet in wallets:
        logging.info(f"Wallet: {wallet['address']} - {wallet['name']} ({wallet['email']}) - Nickname:{wallet['kraken_nickname']} ")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"Script failed: {str(e)}")