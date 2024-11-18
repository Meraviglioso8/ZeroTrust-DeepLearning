import os
import psycopg2
import pyotp  
import requests
import qrcode
import base64
import aiohttp
from io import BytesIO
from barbicanclient import client
from keystoneauth1.identity import v3
from keystoneauth1 import session
from dotenv import load_dotenv
from typing import Optional, List
from psycopg2.extras import RealDictCursor

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
barbican = client.Client(session=sess, endpoint=BARBICAN_URL)

async def get_db_connection():
    """Establish a database connection."""
    try:
        conn = psycopg2.connect(
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        return None

async def generate_totp_uri(email, totp_secret):
    issuer_name = "ZERO-TRUST"  # Replace with your app's name
    return f"otpauth://totp/{issuer_name}:{email}?secret={totp_secret}&issuer={issuer_name}"

async def generate_qr_code(uri):
    qr = qrcode.make(uri)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return qr_base64

# Helper functions for user handling
async def is_duplicate(email: str) -> bool:
    conn = await get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            query = "SELECT email FROM users WHERE email = %s"
            cursor.execute(query, (email,))
            result = cursor.fetchone()
            return result is not None
        finally:
            conn.close()

async def find_user_hashed_password_by_email(email: str) -> Optional[str]:
    conn = await get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            query = "SELECT password FROM users WHERE email = %s"
            cursor.execute(query, (email,))
            result = cursor.fetchone()
            return result["password"] if result else None
        finally:
            conn.close()

async def find_user_id_by_email(email: str) -> Optional[int]:
    conn = await get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            query = "SELECT id FROM users WHERE email = %s"
            cursor.execute(query, (email,))
            result = cursor.fetchone()
            return result["id"] if result else None
        finally:
            conn.close()

async def insert_user(email: str, password_hash: str, totp_secret: str) -> Optional[int]:
    conn = await get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            query = "INSERT INTO users (email, password) VALUES (%s, %s) RETURNING id"
            cursor.execute(query, (email, password_hash))
            user_id = cursor.fetchone()["id"]
            conn.commit()
            await store_secret_in_barbican(user_id, totp_secret)
            return user_id
        finally:
            conn.close()

# Function to store secret in Barbican
async def store_secret_in_barbican(userid: str, secret: str):
    try:
        new_secret = barbican.secrets.create()
        new_secret.name = f'Random plain text password for user {userid}'
        new_secret.payload = secret
        new_secret.store()
    except Exception as e:
        print(f"Error during store secret: {e}")

# Function to retrieve the TOTP secret from Barbican
async def query_secret_by_userid(userid: str) -> Optional[str]:
    try:
        secrets = barbican.secrets.list()
        for secret in secrets:
            if secret.name == f'Random plain text password for user {userid}':
                return secret.payload
        return None
    except Exception as e:
        print(f"Error during secret retrieval: {e}")
        return None

# TOTP Functions for 2FA
async def generate_totp_secret():
    return pyotp.random_base32()

async def verify_totp(email: str, totp_code: str) -> bool:
    user_id = await find_user_id_by_email(email)
    totp_secret = await query_secret_by_userid(user_id)
    if not totp_secret:
        return False
    totp = pyotp.TOTP(totp_secret)
    return totp.verify(totp_code)

# Call the authorization service to request token generation
async def add_permission_to_user(user_id: str, permissions: List[str]) -> Optional[dict]:
    mutation = """
    mutation AddPermission($userId: String!, $permissions: [String!]!) {
        addPermission(userId: $userId, permissions: $permissions) {
            info
            permissions
        }
    }
    """
    variables = {
        "userId": str(user_id),
        "permissions": permissions  # Ensure this is a list of strings
    }

    try:
        # Send the request
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{AUTHORIZATION_API_URL}/authorization",
                json={"query": mutation, "variables": variables}
            ) as response:
                response.raise_for_status()
                return await response.json()
    except aiohttp.ClientError as e:
        print(f"Error sending GraphQL mutation to add permissions: {e}")
        return None

