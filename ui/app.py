from flask import Flask, render_template, request, jsonify
import time

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
        #else:
        # gen = generate()
        # response = gen
    elif button_clicked == "search_one":
        search_data = data.get('email')
        search_query = "email"
        if not search_data:
            search_data = data.get("name")
            search_query = "name"
        if not search_data:
            return jsonify({"Error": "Either name or email is required"}), 400
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
