import os
import psycopg2
import pyotp  
import requests 
import qrcode
import base64
from io import BytesIO
from barbicanclient import client
from keystoneauth1.identity import v3
from keystoneauth1 import session
from dotenv import load_dotenv
from typing import List

# Load environment variables
load_dotenv()

# PostgreSQL connection details
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
POSTGRES_DB = os.getenv('POSTGRES_DB')
POSTGRES_HOST = os.getenv('POSTGRES_HOST')
POSTGRES_PORT = os.getenv('POSTGRES_PORT')

# Authorization API URL (for session management, etc.)
AUTHORIZATION_API_URL = os.getenv('AUTHORIZATION_API_URL')

# OpenStack Barbican (Key Vault) credentials
OS_AUTH_URL = os.getenv('OS_AUTH_URL')
OS_USERNAME = os.getenv('OS_USERNAME')
OS_PASSWORD = os.getenv('OS_PASSWORD')
OS_PROJECT_NAME = os.getenv('OS_PROJECT_NAME')
OS_USER_DOMAIN_NAME = os.getenv('OS_USER_DOMAIN_NAME')
OS_PROJECT_DOMAIN_NAME = os.getenv('OS_PROJECT_DOMAIN_NAME')
BARBICAN_URL = os.getenv('BARBICAN_URL')

# Authenticate with Keystone and create a session for Barbican
auth = v3.Password(auth_url=OS_AUTH_URL,
                   username=OS_USERNAME,
                   password=OS_PASSWORD,
                   project_name=OS_PROJECT_NAME,
                   user_domain_name=OS_USER_DOMAIN_NAME,
                   project_domain_name=OS_PROJECT_DOMAIN_NAME)
sess = session.Session(auth=auth)
barbican = client.Client(session=sess,endpoint=BARBICAN_URL)

print("Auth token:", sess.get_token())

print(barbican)

def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT
        )
        return conn
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        return None

def generate_totp_uri(email, totp_secret):
    issuer_name = "ZERO-TRUST"  # Replace with your app's name
    return f"otpauth://totp/{issuer_name}:{email}?secret={totp_secret}&issuer={issuer_name}"

def generate_qr_code(uri):
    qr = qrcode.make(uri)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return qr_base64  # This can be sent as a base64-encoded string

# Helper functions for user handling
def is_duplicate(email: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT email FROM users WHERE email = %s"
    cursor.execute(query, (email,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result is not None

def find_user_by_email(email: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT id, email, password, permissions FROM users WHERE email = %s"
    cursor.execute(query, (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def insert_user(email: str, password_hash: str, permissions: List[str], totp_secret: str):
    # Store the TOTP secret in Barbican
    
    
    # Insert user into the database without storing the TOTP secret
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "INSERT INTO users (email, password, permissions) VALUES (%s, %s, %s) RETURNING id"
    cursor.execute(query, (email, password_hash, permissions))
    conn.commit()
    user_id = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    store_secret_in_barbican(user_id, totp_secret)
    return user_id

# Function to store secret in Barbican
def store_secret_in_barbican(userid: str, secret: str) -> str:
    # Create a new secret in Barbican
    try:
        new_secret = barbican.secrets.create()
        new_secret.name = u'Random plain text password for user {}'.format(userid)
        new_secret.payload = secret
        new_secret.store()
    except Exception as e:
        print("Error during signup 111:", e)

# Function to retrieve the TOTP secret from Barbican
def retrieve_secret_from_barbican(secret_ref: str) -> str:
    secret = barbican.secrets.get(secret_ref)
    return secret.payload  # Get the payload (secret value)

# TOTP Functions for 2FA
def generate_totp_secret():
    return pyotp.random_base32()

def verify_totp(secret_ref: str, totp_code: str):
    # Retrieve the TOTP secret from Barbican
    totp_secret = retrieve_secret_from_barbican(secret_ref)
    totp = pyotp.TOTP(totp_secret)
    return totp.verify(totp_code)

# Call the authorization service to request token generation
def request_token_from_authorization(user_id: str, permissions: List[str]):
    data = {
        "user_id": user_id,
        "permissions": permissions
    }
    try:
        response = requests.post(f"{AUTHORIZATION_API_URL}/generate-token", json=data)
        response.raise_for_status()  # Raise an error if status code is not 200
        return response.json().get('token')  # Extract token from the response
    except requests.RequestException as e:
        print(f"Failed to request token from authorization service: {e}")
        return None
