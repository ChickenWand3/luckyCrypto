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
def generate_wallets(num_wallets=4, wallets_file="wallets.enc", key_file="encryption_key.txt", user_data=None):
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

def disable_wallet(wallet_email, wallet_name, wallets_file="wallets.enc", key_file="encryption_key.txt"):
    wallets = get_wallets(wallets_file, key_file)
    for wallet in wallets:
        if wallet["email"] == wallet_email or wallet["name"] == wallet_name:
            #LOOOOOK
            #ALSO NEED TO TRANSFER USDC TO MASTER WALLET IF ABOVE 1 USDC
            #CHECK IF ENOUGH GAS TO TRANSFER IF NOT SEND GAS
            #FUNCTIONALITY STILL NEEDED
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
    return False #Couldn't find wallet

# Schedule transfers
def main():
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
    '''
    if not INFURA_API_KEY or not MASTER_PRIVATE_KEY:
        logging.error("Missing INFURA_API_KEY or MASTER_PRIVATE_KEY in .env file")
        raise ValueError("Please set INFURA_API_KEY and MASTER_PRIVATE_KEY in .env file")
    '''
    
    if not web3.is_connected():
        logging.error("Failed to connect to Ethereum mainnet")
        raise ConnectionError("Cannot connect to Ethereum mainnet")

    #generate_wallets(num_wallets=5)
    #wallets = get_wallets()

    generate_wallets(num_wallets=1, wallets_file="masterWallets.enc", key_file="masterEncryption_key.txt", user_data=[{"name": "Ashton", "email": "cgservicesofficial@gmail.com"}]) # Generate a masterWallet for testing
    wallets = get_wallets(wallets_file="masterWallets.enc", key_file="masterEncryption_key.txt")

    for wallet in wallets:
        logging.info(f"Wallet: {wallet['address']} - {wallet['name']} ({wallet['email']}) - Balance: {usdc_contract.functions.balanceOf(wallet['address']).call() / 10**6} USDC")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"Script failed: {str(e)}")