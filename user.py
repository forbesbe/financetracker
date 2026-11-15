import hashlib
import json
import re
import secrets
import hmac

from flask import Blueprint, request, session

import db

user_bp = Blueprint('user', __name__)

def pw_check(password, first_name, last_name, username):
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    if (
        first_name.lower() in password.lower() or
        last_name.lower() in password.lower() or
        username.lower() in password.lower()
    ):
        return False
    return True

@user_bp.route('/create_user', methods=['POST'])
def create_user():

    data = request.get_json() or {}
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    salt = secrets.token_hex(16)

    if not all([first_name, last_name, username, email, password]):
        response_data = {'status': 2, "message": "Please fill all required fields."}
        return json.dumps(response_data), 200, {'Content-Type': 'application/json'}

    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM users WHERE username = ?", (username,))
        existing_user = cursor.fetchone()
        if existing_user:
            response_data = {'status': 3, "message": "User already exists."}
            return json.dumps(response_data), 200, {'Content-Type': 'application/json'}

        cursor.execute("SELECT 1 FROM users WHERE email_address = ?", (email,))
        existing_email = cursor.fetchone()
        if existing_email:
            response_data = {'status': 4, "message": "Email already exists."}
            return json.dumps(response_data), 200, {'Content-Type': 'application/json'}

        if not pw_check(password, first_name, last_name, username):
            response_data = {'status': 5, "message": "Password must contain a capital letter, "
                                                     "lowercase letter, number, special character, "
                                                     "and be at least 8 characters long."}
            return json.dumps(response_data), 200, {'Content-Type': 'application/json'}

        pass_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 600_000).hex()

        cursor.execute("""
        INSERT INTO users (first_name, last_name, username, email_address, password, salt)
        VALUES (?, ?, ?, ?, ?, ?)""", (first_name, last_name, username, email, pass_hash, salt))
        conn.commit()
        response_data = {'status': 1, "message": "User created successfully."}
        session['user_id'] = cursor.lastrowid
        return json.dumps(response_data), 200, {'Content-Type': 'application/json'}
    finally:
        conn.close()

@user_bp.route('/login', methods=['POST'])
def login():

    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')

    if not all([username, password]):
        response_data = {'status': 2, "message": "Please fill all required fields."}
        return json.dumps(response_data), 200, {'Content-Type': 'application/json'}

    conn = db.get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, password, salt FROM users WHERE username = ?", (username,))
        user_data = cursor.fetchone()

        if not user_data:
            response_data = {'status': 3, "message": "User does not exist."}
            return json.dumps(response_data), 200, {'Content-Type': 'application/json'}

        user_id, db_pass, salt = user_data
        hashed_input_password = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 600_000).hex()

        if not hmac.compare_digest(hashed_input_password, db_pass):
            response_data = {'status': 4, "message": "Stored password does not match."}
            return json.dumps(response_data), 200, {'Content-Type': 'application/json'}

        response_data = {'status': 1, "message": "Login successful."}
        session['user_id'] = user_id
        return json.dumps(response_data), 200, {'Content-Type': 'application/json'}
    finally:
        conn.close()

@user_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    response_data = {'status': 1, "message": "Logged out successfully."}
    return json.dumps(response_data), 200, {'Content-Type': 'application/json'}
