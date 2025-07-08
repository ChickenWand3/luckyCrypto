from flask import Flask, render_template, request, jsonify
import time

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/process', methods=['POST'])
def process():
    data = request.json
    user_input = data.get('user_input')
    button_clicked = data.get('button')
    result = f"You entered: {user_input} and clicked: {button_clicked}"
    time.sleep(2)  # Simulate a long-running process
    print(data)
    return jsonify({"result": result})

#@app.route('/menu1')
#def menu1():
#    return "<h1>Menu 1 Page</h1><p>This is Menu 1 content.</p><a href='/'>Go Back</a>"
#
#@app.route('/menu2')
#def menu2():
#    return "<h1>Menu 2 Page</h1><p>This is Menu 2 content.</p><a href='/'>Go Back</a>"

if __name__ == '__main__':
    app.run(debug=True)
