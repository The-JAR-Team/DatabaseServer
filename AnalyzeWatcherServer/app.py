from flask import Flask

app = Flask(__name__)

# Define a route
@app.route('/')
def home():
    return "Hello, Flask!"

# Run the server
if __name__ == '__main__':
    app.run(debug=True)