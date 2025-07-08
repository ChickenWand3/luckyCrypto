import os
import json
import time
import logging
from web3 import Web3
from eth_account import Account
from cryptography.fernet import Fernet
from dotenv import load_dotenv

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