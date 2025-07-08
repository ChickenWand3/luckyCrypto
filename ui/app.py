from flask import Flask, render_template, request, jsonify
import time

import sys, os
sys.path.append("..")  # Adjust the path to import from the parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from funcs import generate_wallets, search_wallets

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/action', methods=['POST'])
def action():
    data = request.json
    if not data:
        return jsonify({"Error": "No data provided"}), 400
    user_input = data.get('user_input')
    button_clicked = data.get('button')
    if button_clicked == "generate":
        user_name = data.get('name')
        user_email = data.get('email')
        if not user_name or not user_email:
            return jsonify({"Error": "Name and email are both required"}), 400
        else:
            user_data = [{"name": user_name, "email": user_email}]
            try:
                print("Gen")
                gen = generate_wallets(num_wallets=len(user_data), user_data=user_data)
                if gen:
                    print(f"Wallets generated successfully with attributes: {user_name} & {user_email}")
                    return jsonify({"result": f"Wallets generated successfully with attributes: {user_name} & {user_email}"}), 200
                else:
                    return jsonify({"Error": f"Failed to generate wallets: {gen}"}), 500
            except Exception as e:
                return jsonify({"Error": f"An internal error occurred: {str(e)}"}), 500
    elif button_clicked == "search_one":
        search_email = data.get('email')
        search_name = data.get('name')
        if not search_email and not search_name:
            return jsonify({"Error": "At least one of name or email is required for search"}), 400
        try:
            search_results = search_wallets(wallet_name=search_name, wallet_email=search_email)
            if search_results:
                print(f"Search results: {search_results}")
                return jsonify({"result": f"Search results: {search_results}"}), 200
            else:
                return jsonify({"Error": "No wallets found matching the search criteria"}), 404
        except Exception as e:
            return jsonify({"Error": f"An internal error occurred: {str(e)}"}), 500
    #result = f"You entered: {user_input} and clicked: {button_clicked}"
    
    time.sleep(2)  # Simulate a long-running process
    print(data)
    
    #return jsonify({"result": result})

#@app.route('/menu1')
#def menu1():
#    return "<h1>Menu 1 Page</h1><p>This is Menu 1 content.</p><a href='/'>Go Back</a>"
#
#@app.route('/menu2')
#def menu2():
#    return "<h1>Menu 2 Page</h1><p>This is Menu 2 content.</p><a href='/'>Go Back</a>"

if __name__ == '__main__':
    app.run(debug=True)
