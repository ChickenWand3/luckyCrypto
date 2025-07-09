from flask import Flask, render_template, request, jsonify
import time, threading
import sys, os
import logging
from dotenv import load_dotenv
from web3 import Web3
from pycoingecko import CoinGeckoAPI
import krakenex

sys.path.append("..")  # Adjust the path to import from the parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from funcs import generate_wallets, search_wallets, get_wallets, disable_wallet, jsonify_walletBalances

from send_out_gas import refillGas
from sweep_to_main import main as sweep_to_main

app = Flask(__name__)

async def sweep_to_main_async():
    return await sweep_to_main()
def run_refill_gas_async():
    try:
        refillGas()
        logging.info("Gas refill completed.")
    except Exception as e:
        logging.error(f"Error during refillGas: {str(e)}")


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/action', methods=['POST'])
async def action():
    print("Received request:", request.json)
    data = request.json
    if not data:
        return jsonify({"result": "No data provided"}), 400
    
    button_clicked = data.get('button')
    if button_clicked == "generate":
        user_name = data.get('name')
        user_email = data.get('email')
        if not user_name or not user_email:
            return jsonify({"result": "Name and email are both required"}), 400
        else:
            user_data = [{"name": user_name, "email": user_email}]
            try:
                gen = generate_wallets(num_wallets=len(user_data), user_data=user_data)
                if gen:
                    return jsonify({"result": f"Wallets generated successfully with attributes: {user_name} & {user_email}"}), 200
                else:
                    return jsonify({"result": f"Failed to generate wallets: {gen}"}), 500
            except Exception as e:
                return jsonify({"result": f"An internal error occurred: {str(e)}"}), 500
    elif button_clicked == "search_one":
        search_email = data.get('email')
        search_name = data.get('name')
        if not search_email and not search_name:
            return jsonify({"result": "At least one of name or email is required for search"}), 400
        try:
            search_results = search_wallets(wallet_name=search_name, wallet_email=search_email)
            if search_results:
                return jsonify({"result": search_results}), 200
            else:
                return jsonify({"result": "No wallets found matching the search criteria"}), 404
        except Exception as e:
            return jsonify({"result": f"An internal error occurred: {str(e)}"}), 500
    elif button_clicked == "delete":
        if data.get('searchType') == 'name':
            delete_email = None
            delete_name = data.get('value')
        elif data.get('searchType') == 'email':
            delete_name = None
            delete_email = data.get('value')
        else:
            return jsonify({"result": "Invalid search type provided"}), 400
        if not delete_email and not delete_name:
            return jsonify({"result": "At least one of name or email is required for deletion"}), 400
        try:
            deleted = disable_wallet(wallet_email=delete_email, wallet_name=delete_name)
            if deleted:
                return jsonify({"result": "Wallet disabled successfully"}), 200
            else:
                return jsonify({"result": "No matching wallet found to disable"}), 404
        except Exception as e:
            return jsonify({"result": f"An internal error occurred: {str(e)}"}), 500
    elif button_clicked == "list_all":
        scope = data.get('scope', 'all')
        try:
            wallets = get_wallets()
            if scope.lower() == 'enabled':
                wallets = [wallet for wallet in wallets if wallet.get("enabled", True)]  # Filter enabled wallets
            elif scope.lower() == 'disabled':
                wallets = [wallet for wallet in wallets if not wallet.get("enabled", True)]
            if wallets:
                return jsonify({"result": wallets}), 200
            else:
                return jsonify({"result": "No wallets found"}), 404
        except Exception as e:
            return jsonify({"result": f"An internal error occurred: {str(e)}"}), 500
    elif button_clicked == "force_sweep":
        try:
            swept = await sweep_to_main_async()
            if swept:
                return jsonify({"result": "Sweep operation completed successfully"}), 200
            else:
                return jsonify({"result": "Sweep operation failed"}), 500
        except Exception as e:
            return jsonify({"result": f"An internal error occurred during sweep: {str(e)}"}), 500
    elif button_clicked == "list_all_balances":
        scope = data.get('scope', 'all')
        try:
            wallets = get_wallets()
            if scope.lower() == 'enabled':
                wallets = [wallet for wallet in wallets if wallet.get("enabled", True)]  # Filter enabled wallets
            elif scope.lower() == 'disabled':
                wallets = [wallet for wallet in wallets if not wallet.get("enabled", True)]
            wallets_balances = jsonify_walletBalances(wallets=wallets)
            if not wallets_balances["wallets"]:
                return jsonify({"result": "No wallets found or no balances available"}), 404
            else:
                return jsonify({"result": wallets_balances["wallets"]}), 200
        except Exception as e:
            return jsonify({"result": f"An internal error occurred: {str(e)}"}), 500
    elif button_clicked == "refill_gas":
       try:
           thread = threading.Thread(target=run_refill_gas_async)
           thread.start()
           return jsonify({"result": "Gas refill operation started"}), 200
       except Exception as e:
           return jsonify({"result": f"An internal error occurred during gas refill: {str(e)}"}), 500
    return jsonify({"result": "Undefined Action"}), 400


if __name__ == '__main__':
    # Set up logging
    logging.basicConfig(filename='usdc_transfer.log', level=logging.INFO, 
                        format='%(asctime)s - %(levelname)s - %(message)s')
    # Load environment variables
    load_dotenv()
    INFURA_API_KEY = os.getenv('INFURA_API_KEY')
    KRAKEN_API_KEY = os.getenv('KRAKEN_API_KEY')
    KRAKEN_API_SECRET = os.getenv('KRAKEN_API_SECRET')

    MAINNET_RPC_URL = f"https://mainnet.infura.io/v3/{INFURA_API_KEY}"

    # Initialize web3, CoinGecko, and Kraken
    web3 = Web3(Web3.HTTPProvider(MAINNET_RPC_URL))
    cg = CoinGeckoAPI()
    kraken = krakenex.API(key=KRAKEN_API_KEY, secret=KRAKEN_API_SECRET)
    app.run(debug=True)
