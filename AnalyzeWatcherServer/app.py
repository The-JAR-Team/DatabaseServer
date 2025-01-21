from flask import Flask, request, jsonify
from google.oauth2 import id_token
from google.auth.transport import requests
import pymysql
from dotenv import load_dotenv
import os

app = Flask(__name__)

# Load environment variables from the .env file
load_dotenv()

# Access environment variables
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

# Database connection function
def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
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
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                # Check if the user exists
                cursor.execute(f"SELECT * FROM User WHERE google_id = '{google_id}'")
                user = cursor.fetchone()

                if not user:
                    # Insert new user if not found
                    cursor.execute(
                        f"""
                        INSERT INTO User (google_id, first_name, last_name, email)
                        VALUES ('{google_id}', '{idinfo.get("given_name")}', '{idinfo.get("family_name")}', '{email}')
                        """
                    )
                    connection.commit()

                    cursor.execute(f"SELECT * FROM User WHERE google_id = '{google_id}'")
                    user = cursor.fetchone()

                print(f"User data: {user}")
                return jsonify({"success": True, "user": user}), 200

    except ValueError as e:
        # Invalid token
        return jsonify({"success": False, "message": str(e)}), 401

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/videos', methods=['GET'])
def get_videos():
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                # Fetch videos categorized by subject
                cursor.execute("""
                    SELECT v.subject_name, v.video_id, v.name, v.description 
                    FROM Video v
                    LEFT JOIN Video_Subject vs ON v.subject_name = vs.subject_name
                    ORDER BY v.subject_name, v.name
                """)
                videos = cursor.fetchall()

                if not videos:
                    print("No videos found in the database.")
                    return jsonify({"success": True, "videos": {}}), 200

                # Organize videos by subject
                categorized_videos = {}
                for video in videos:
                    subject = video.get('subject_name') or 'Uncategorized'
                    if subject not in categorized_videos:
                        categorized_videos[subject] = []
                    categorized_videos[subject].append({
                        "video_id": video.get('video_id'),
                        "name": video.get('name'),
                        "description": video.get('description')
                    })

                return jsonify({"success": True, "videos": categorized_videos}), 200
    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        return jsonify({"success": False, "message": "Database error occurred"}), 500
    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({"success": False, "message": "An unexpected error occurred"}), 500



@app.route('/upload', methods=['POST'])
def upload_video():
    data = request.json
    subject = data.get('subject')
    video_name = data.get('videoName')
    description = data.get('description')

    if not subject or not video_name:
        return jsonify({"success": False, "message": "Missing required fields"}), 400

    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                # Ensure the subject exists
                cursor.execute(f"SELECT * FROM Video_Subject WHERE subject_name = '{subject}'")
                if not cursor.fetchone():
                    cursor.execute(f"INSERT INTO Video_Subject (subject_name) VALUES ('{subject}')")
                    connection.commit()

                # Insert into the Video table
                cursor.execute(
                    f"""
                    INSERT INTO Video (upload_type, name, description, subject_name, added_date)
                    VALUES ('YouTube', '{video_name}', '{description}', '{subject}', NOW())
                    """
                )
                connection.commit()

                video_id = cursor.lastrowid  # Get the last inserted ID

                # Insert into the YouTube_Video table
                cursor.execute(f"INSERT INTO YouTube_Video (video_id) VALUES ({video_id})")
                connection.commit()

        return jsonify({"success": True, "message": "Video uploaded successfully"}), 201
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
