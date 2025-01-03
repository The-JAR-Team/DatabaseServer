from flask import Flask, request, jsonify
from flask_cors import CORS
from google.oauth2 import id_token
from google.auth.transport import requests
import pymysql
from dotenv import load_dotenv
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

CORS(app, resources={r"/login": {"origins": "http://localhost:3000"}})


# Database connection function
def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="1234",
        database="MyDatabase",
        cursorclass=pymysql.cursors.DictCursor
    )


@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        print(f"Received data: {data}")  # Log received data

        token = data.get('token')
        if not token:
            return jsonify({"success": False, "message": "No token provided"}), 400

        # Verify the token
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)
        print(f"Token verified. ID Info: {idinfo}")

        # Extract user information
        google_id = idinfo["sub"]
        email = idinfo["email"]
        print(f"User verified: google_id={google_id}, email={email}")

        # Connect to the database
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # Check if the user exists
                sql = "SELECT * FROM User WHERE google_id = %s"
                cursor.execute(sql, (google_id,))
                user = cursor.fetchone()

                if not user:
                    # Insert new user if not found
                    sql = "INSERT INTO User (google_id, first_name, last_name, email) VALUES (%s, %s, %s, %s)"
                    cursor.execute(sql, (google_id, idinfo.get("given_name"), idinfo.get("family_name"), email))
                    connection.commit()
                    cursor.execute("SELECT * FROM User WHERE google_id = %s", (google_id,))
                    user = cursor.fetchone()

                print(f"User data: {user}")
                return jsonify({"success": True, "user": user}), 200
        finally:
            connection.close()


    except ValueError as e:
        # Invalid token
        return jsonify({"success": False, "message": str(e)}), 401

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
