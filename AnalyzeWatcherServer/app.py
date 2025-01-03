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

@app.route('/videos', methods=['GET'])
def get_videos():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Fetch videos categorized by subject
            sql = """
                SELECT v.subject_name, v.video_id, v.name, v.description 
                FROM Video v
                LEFT JOIN Video_Subject vs ON v.subject_name = vs.subject_name
                ORDER BY v.subject_name, v.name;
            """
            cursor.execute(sql)
            videos = cursor.fetchall()

            # Organize videos by subject
            categorized_videos = {}
            for video in videos:
                subject = video['subject_name'] or 'Uncategorized'
                if subject not in categorized_videos:
                    categorized_videos[subject] = []
                categorized_videos[subject].append({
                    "video_id": video['video_id'],
                    "name": video['name'],
                    "description": video['description']
                })

            return jsonify({"success": True, "videos": categorized_videos}), 200
    finally:
        connection.close()


@app.route('/upload', methods=['POST'])
def upload_video():
    data = request.json
    subject = data.get('subject')
    videoId = data.get('videoId')
    videoName = data.get('videoName')
    description = data.get('description')

    if not subject or not videoId or not videoName:
        return jsonify({"success": False, "message": "Missing required fields"}), 400

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Ensure the subject exists
            cursor.execute("SELECT * FROM Video_Subject WHERE subject_name = %s", (subject,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO Video_Subject (subject_name) VALUES (%s)", (subject,))
                connection.commit()

            # Insert into the Video table
            cursor.execute(
                """
                INSERT INTO Video (upload_type, name, description, subject_name, added_date)
                VALUES (%s, %s, %s, %s, NOW())
                """,
                ("YouTube", videoName, description, subject)
            )
            connection.commit()
            video_id = cursor.lastrowid  # Get the last inserted ID

            # Insert into the YouTube_Video table
            cursor.execute(
                "INSERT INTO YouTube_Video (video_id) VALUES (%s)",
                (video_id,)
            )
            connection.commit()

        return jsonify({"success": True, "message": "Video uploaded successfully"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        connection.close()

if __name__ == '__main__':
    app.run(debug=True)