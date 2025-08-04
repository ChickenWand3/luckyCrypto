from web3 import Web3
import os
from dotenv import load_dotenv

load_dotenv()
INFURA_API_KEY = os.getenv("INFURA_API_KEY")
KRAKEN_ADDRESS = os.getenv("KRAKEN_ADDRESS")
KRAKEN_ADDRESS = Web3.to_checksum_address(KRAKEN_ADDRESS)

# Connect to Ethereum node
web3 = Web3(Web3.HTTPProvider(f"https://mainnet.infura.io/v3/{INFURA_API_KEY}"))

# Example sender address and private key
sender_address = '0xe18f986B9FD463e049B0c8Bb4412f4c4F599EA3D'
private_key = '0x8565fa2ef961e4bc7d47e6fec945c84496a243070a21f3a45ba743bc6b86241f'
    
def cancel_pending_transaction(address, private_key, web3):
    # Get the nonce of the first pending transaction
    nonce = web3.eth.get_transaction_count(sender_address, 'latest')

    if nonce is not None:
        # Build a cancellation transaction (self-transfer of 0 ETH)
        tx = {
            'from': address,
            'to': address,  # Self-transfer to cancel
            'value': 0,  # No ETH sent
            'nonce': nonce,
            'gas': 21000,  # Standard gas limit for simple ETH transfer
            'chainId': web3.eth.chain_id
        }

        # Get current gas price and increase it by 20% to ensure replacement
        current_gas_price = web3.eth.gas_price
        new_gas_price = int(current_gas_price * 1.2)  # 20% higher gas price

        tx['gasPrice'] = new_gas_price

        # Estimate gas (should be 21000 for a simple transfer, but confirm)
        estimated_gas = web3.eth.estimate_gas(tx)
        tx['gas'] = estimated_gas

        # Sign the transaction
        signed_tx = web3.eth.account.sign_transaction(tx, private_key)

        # Send the transaction
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        # Calculate total cost in ETH
        total_gas_cost_eth = web3.from_wei(estimated_gas * new_gas_price, 'ether')

        print(f"Cancel transaction sent. Transaction hash: {tx_hash.hex()}")
        print(f"Nonce used: {nonce}")
        print(f"Estimated gas: {estimated_gas}")
        print(f"New gas price (wei): {new_gas_price}")
        print(f"Total estimated cost in ETH: {total_gas_cost_eth}")
    else:
        print("No transaction to cancel.")

def main():
    cancel_pending_transaction(sender_address, private_key, web3)

if __name__ == "__main__":
    main()



