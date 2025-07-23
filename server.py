# main.py
# This is a simple Flask server to act as the middleman for the remote keyboard.
# To run this:
# 1. Install Flask and Flask-CORS: pip install Flask Flask-CORS
# 2. Run the server: python main.py
# On an AWS EC2 instance, you would run this using a production server like Gunicorn.

from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import string

# Initialize the Flask app
app = Flask(__name__)
# Enable Cross-Origin Resource Sharing (CORS) to allow our mobile app
# and desktop client to communicate with the server.
CORS(app)

# This dictionary will act as our simple in-memory "database".
# It will store the connection code and the text to be typed.
# Format: { 'code': 'text_to_type' }
# Example: { '123456': 'Hello from my phone!' }
connections = {}

def generate_code(length=6):
    """Generates a random alphanumeric code."""
    while True:
        # Generate a new code
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        # Ensure the code is not already in use
        if code not in connections:
            return code

@app.route('/')
def index():
    """A simple index route to confirm the server is running."""
    return "Remote Keyboard Server is running!"

@app.route('/get-code', methods=['GET'])
def get_code():
    """
    Generates a unique code for the PC client to use.
    The PC app will call this endpoint first.
    """
    code = generate_code()
    # Store the new code with an empty text value
    connections[code] = ""
    print(f"New connection code generated: {code}. Current connections: {connections}")
    return jsonify({'code': code})

@app.route('/send-text', methods=['POST'])
def send_text():
    """
    Receives text from the mobile app and associates it with a code.
    The mobile app will call this endpoint.
    """
    data = request.get_json()
    if not data or 'code' not in data or 'text' not in data:
        return jsonify({'status': 'error', 'message': 'Invalid data. Required: code, text'}), 400

    code = data['code']
    text = data['text']

    if code not in connections:
        return jsonify({'status': 'error', 'message': 'Invalid connection code'}), 404

    # Store the text for the given code
    connections[code] = text
    print(f"Received text for code {code}: '{text}'. Current connections: {connections}")
    return jsonify({'status': 'success', 'message': 'Text received'})

@app.route('/get-text/<string:code>', methods=['GET'])
def get_text(code):
    """
    Provides text to the PC client.
    The PC app will poll this endpoint continuously.
    """
    if code not in connections:
        return jsonify({'status': 'error', 'message': 'Invalid connection code'}), 404

    # Get the text associated with the code
    text_to_type = connections[code]

    if text_to_type:
        # Clear the text after sending it so it's not typed again
        connections[code] = ""
        print(f"Sent text to PC with code {code}: '{text_to_type}'.")
        return jsonify({'text': text_to_type})
    else:
        # If there's no new text, return an empty string
        return jsonify({'text': ''})

@app.route('/close-connection/<string:code>', methods=['POST'])
def close_connection(code):
    """
    Allows the PC client to remove its code from the server when it closes.
    """
    if code in connections:
        del connections[code]
        print(f"Connection closed for code: {code}. Current connections: {connections}")
        return jsonify({'status': 'success', 'message': 'Connection closed'})
    return jsonify({'status': 'error', 'message': 'Invalid code'}), 404


if __name__ == '__main__':
    # Running on 0.0.0.0 makes the server accessible from other devices on the same network.
    # For AWS, you would configure a security group to allow traffic on port 5000.
    app.run(host='0.0.0.0', port=5000, debug=True)
