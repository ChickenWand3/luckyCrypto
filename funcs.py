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

def save_wallets(wallets, mnemonic, wallets_file="wallets.enc", key_file="encryption_key.txt"):
    data = {
        "metadata": {
            "mnemonic": mnemonic
        },
        "wallets": wallets
    }

    # Save wallets securely
    logging.info("Saving wallets securely...")
    key = Fernet.generate_key()
    cipher = Fernet(key)
    with open(wallets_file, "wb") as f:
        f.write(cipher.encrypt(json.dumps(data).encode()))
    with open(key_file, "wb") as f:
        f.write(key)

def get_mnemonic(wallets_file="wallets.enc", key_file="encryption_key.txt"):
    if os.path.exists(wallets_file) and os.path.exists(key_file):
        logging.info("Loading existing wallets")
        with open(key_file, "rb") as f:
            key = f.read()
        cipher = Fernet(key)
        with open(wallets_file, "rb") as f:
            encrypted_data = f.read()
        data = json.loads(cipher.decrypt(encrypted_data).decode())
        mnemonic = data["metadata"]["mnemonic"]
        return mnemonic
    else:
        logging.error("Wallets file or key file does not exist")
        return None

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
                #"mnemonic": mnemonic,
                "name": user_data[i]["name"],
                "email": user_data[i]["email"],
                "kraken_nickname": f"Wallet#{highest_index + 1 + i}",
                "enabled": True
            })
            logging.info(f"Generated new wallet with address_index {highest_index + 1 + i}: {account.address}")
        
        # Append new wallets to existing list
        wallets.extend(new_wallets)
        save_wallets(wallets, mnemonic, wallets_file, key_file)

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
                #"mnemonic": mnemonic,
                "name": user_data[i]["name"],
                "email": user_data[i]["email"],
                "kraken_nickname": f"Wallet#{i}",
                "enabled": True
            })

            logging.info(f"Generated wallet with address_index {i}: {account.address}")
        
        save_wallets(wallets, mnemonic, wallets_file, key_file)
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
    

def transfer_eth_to_enabled_wallet(wallet, wallets, min_transfer_eth=0.001):
    try:
        # Load environment variables
        load_dotenv()
        INFURA_API_KEY = os.getenv("INFURA_API_KEY")

        # Initialize Web3
        infura_url = f"https://mainnet.infura.io/v3/{INFURA_API_KEY}"
        web3 = Web3(Web3.HTTPProvider(infura_url))
        if not web3.is_connected():
            raise ConnectionError("Failed to connect to Infura")

        # Validate and convert source wallet address to checksum format
        source_address = web3.to_checksum_address(wallet["address"])
        private_key = wallet["private_key"]

        # Find another enabled wallet
        destination_wallet = None
        for w in wallets:
            if w.get("enabled", False) and w["address"].lower() != wallet["address"].lower():
                try:
                    destination_address = web3.to_checksum_address(w["address"])
                    destination_wallet = w
                    break
                except ValueError:
                    logging.warning(f"Invalid address in wallet: {w['address']}, skipping")
                    continue

        if not destination_wallet:
            logging.error("No other enabled wallet found for transfer")
            return False

        logging.info(f"Transferring ETH from {source_address} to {destination_address}")

        # Get ETH balance
        eth_balance = web3.eth.get_balance(source_address)
        balance_eth = web3.from_wei(eth_balance, "ether")
        logging.info(f"Source wallet balance: {eth_balance} wei ({balance_eth:.6f} ETH)")

        if eth_balance == 0:
            logging.info(f"No ETH to transfer from {source_address}")
            return True

        # Get gas price (EIP-1559 compatible)
        latest_block = web3.eth.get_block("latest")
        base_fee = latest_block.get("baseFeePerGas", web3.eth.gas_price)
        max_priority_fee = web3.eth.max_priority_fee or web3.to_wei(2, "gwei")
        gas_price = base_fee + max_priority_fee
        logging.info(f"Gas price: {web3.from_wei(gas_price, 'gwei'):.2f} Gwei (base: {web3.from_wei(base_fee, 'gwei'):.2f}, priority: {web3.from_wei(max_priority_fee, 'gwei'):.2f})")

        # Estimate gas (use 21000 for standard ETH transfer, fallback to estimate_gas)
        gas_limit = 21000
        try:
            estimated_gas = web3.eth.estimate_gas({
                "to": destination_address,
                "value": eth_balance,
                "from": source_address
            })
            if estimated_gas > gas_limit:
                logging.warning(f"Estimated gas ({estimated_gas}) exceeds standard 21000, using estimated value")
                gas_limit = estimated_gas
        except Exception as e:
            logging.warning(f"Gas estimation failed: {e}, using default 21000 gas")

        # Calculate gas cost
        gas_cost_wei = gas_limit * gas_price
        gas_cost_eth = web3.from_wei(gas_cost_wei, "ether")
        logging.info(f"Gas limit: {gas_limit}, Gas cost: {gas_cost_eth:.6f} ETH")

        # Check if balance is sufficient
        if eth_balance <= gas_cost_wei:
            logging.info(f"ETH balance ({balance_eth:.6f} ETH) is less than gas cost ({gas_cost_eth:.6f} ETH), skipping transfer")
            return True
        if balance_eth < float(min_transfer_eth) + float(gas_cost_eth):
            logging.info(f"ETH balance ({balance_eth:.6f} ETH) is less than minimum transfer ({min_transfer_eth} ETH) + gas cost ({gas_cost_eth:.6f} ETH), skipping transfer")
            return True

        # Adjust value to account for gas cost
        transfer_value = eth_balance - gas_cost_wei
        logging.info(
            f"Transferring {web3.from_wei(transfer_value, 'ether'):.6f} ETH to {destination_address}")

        # Build transaction (EIP-1559 compatible)
        tx = {
            "to": destination_address,
            "value": transfer_value,
            "gas": gas_limit,
            "maxFeePerGas": gas_price,
            "maxPriorityFeePerGas": max_priority_fee,
            "nonce": web3.eth.get_transaction_count(source_address),
            "chainId": web3.eth.chain_id,
        }

        # Sign the transaction
        signed_tx = web3.eth.account.sign_transaction(tx, private_key)

        # Send the transaction
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        logging.info(f"ETH transfer sent: {tx_hash.hex()}, transferring {web3.from_wei(transfer_value, 'ether'):.6f} ETH with gas price {web3.from_wei(gas_price, 'gwei'):.2f} Gwei")

        return True

    except Exception as e:
        logging.error(f"Error during ETH transfer: {e}")
        return False
        

def disable_wallet(wallet_email, wallet_name, wallets_file="wallets.enc", key_file="encryption_key.txt"):
    wallets = get_wallets(wallets_file, key_file)
    mnemonic = get_mnemonic(wallets_file, key_file)
    for wallet in wallets:
        if (wallet["email"] == wallet_email or wallet["name"] == wallet_name) and wallet.get("enabled", True):

            if transfer_usdc_if_above_one(wallet["address"], wallet["private_key"]):
                logging.info(f"Transferred USDC from {wallet['address']} to master wallet before disabling")

            if transfer_eth_to_enabled_wallet(wallet, wallets, min_transfer_eth=0.001):
                logging.info(f"Transferred ETH from {wallet['address']} to other wallet before disabling")
            
            wallet["enabled"] = False
            logging.info(f"Disabled wallet for email: {wallet_email}")

            save_wallets(wallets, mnemonic, wallets_file, key_file)
            if wallet["name"] == wallet_name:
                logging.info(f"Disabled wallet for name: {wallet_name}")
            elif wallet["email"] == wallet_email:
                logging.info(f"Disabled wallet for email: {wallet_email}")
            return True
    logging.info(f"No valid matching wallet found for email: {wallet_email} or name: {wallet_name}")
    return False #Couldn't find wallet

#COPY PASTA FROM DISABLE IMPLEMENTATION THE SAME
def enable_wallet(wallet_email, wallet_name, wallets_file="wallets.enc", key_file="encryption_key.txt"):
    wallets = get_wallets(wallets_file, key_file)
    mnemonic = get_mnemonic(wallets_file, key_file)
    for wallet in wallets:
        if (wallet["email"] == wallet_email or wallet["name"] == wallet_name) and not wallet.get("enabled", True):
            
            wallet["enabled"] = True

            save_wallets(wallets, mnemonic, wallets_file, key_file)
            if wallet["name"] == wallet_name:
                logging.info(f"Enabled wallet for name: {wallet_name}")
            elif wallet["email"] == wallet_email:
                logging.info(f"Enabled wallet for email: {wallet_email}")
            return True
    logging.info(f"No valid matching wallet found for email: {wallet_email} or name: {wallet_name}")
    return False #Couldn't find wallet


class CustomFileReader:
    def __init__(self, file_path, mode='rb', encoding='utf-8'):
        self.file_path = file_path
        self.mode = mode
        self.encoding = encoding
        self.file = None

    def __enter__(self):
        if 'b' in self.mode:
            self.file = open(self.file_path, self.mode)  # Binary mode: no encoding
        else:
            self.file = open(self.file_path, self.mode, encoding=self.encoding)  # Text mode
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            self.file.close()

    def read(self):
        return self.file.read()

    def readline(self):
        return self.file.readline()

    def readlines(self):
        return self.file.readlines()
    
    def read_last_n_lines(self, n):
        # If n is more than number of lines total, it will return all lines
        if self.file:
            # Go to end of file
            self.file.seek(0, 2)

            # Get position
            pos = self.file.tell()
            # Initialize num lines, result lines
            num_lines = 0
            result_lines = []
            while pos > 0: # While not at beginning of file (prevent going backwards too far)
                # Move position of file pointer backwards and read 1 byte. Compare is newline
                pos -= 1
                self.file.seek(pos)
                if self.file.read(1) == b'\n':
                    num_lines += 1
                    if num_lines == n: # If we reached our goal of going back n lines, return the lines decoded. File must be opened in binary mode
                        for line in self.readlines():
                                result_lines.append(line.decode())
                        return result_lines
        else:
            return None
def read_last_n_lines(num_lines: int, file_name="usdc_transfer.log"):
    with CustomFileReader(file_name, "rb") as f:
        return f.read_last_n_lines(num_lines)

# Schedule transfers
def main():
    # Set up logging
    logging.basicConfig(filename='usdc_transfer.log', level=logging.INFO, 
                        format='%(asctime)s - %(levelname)s - %(message)s')

    #generate_wallets(num_wallets=1)
    wallets = get_wallets()

    disable_wallet(wallet_email="None", wallet_name="Ashton Hulsey", wallets_file="wallets.enc", key_file="encryption_key.txt")
    enable_wallet(wallet_email="None", wallet_name="Ashton Hulsey", wallets_file="wallets.enc", key_file="encryption_key.txt")

    #logging.info(jsonify_walletBalances(wallets_file="wallets.enc", key_file="encryption_key.txt", wallets=wallets))



    for wallet in wallets:
        logging.info(f"Wallet: {wallet['address']} - {wallet['name']} ({wallet['email']}) - Nickname:{wallet['kraken_nickname']} ")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"Script failed: {str(e)}")