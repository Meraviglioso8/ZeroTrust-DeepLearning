import os
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
from typing import List
import re
import aiohttp
import logging

# Load environment variables
load_dotenv()

# PostgreSQL connection details
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
POSTGRES_DB = os.getenv('POSTGRES_DB')
POSTGRES_HOST = os.getenv('POSTGRES_HOST')
POSTGRES_PORT = os.getenv('POSTGRES_PORT')
SESSION_API_URL = os.getenv("SESSION_API_URL", "http://localhost:5003")

# Set up logging
logging.basicConfig(level=logging.INFO)

# Establish a PostgreSQL connection pool
try:
    db_pool = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
    )
    if db_pool:
        logging.info("PostgreSQL connection pool created successfully")
except Exception as e:
    logging.error(f"Error creating PostgreSQL connection pool: {e}")

# Database connection helper functions
def get_db_connection():
    try:
        return db_pool.getconn()
    except Exception as e:
        logging.error(f"Error getting connection from pool: {e}")
        return None

def release_db_connection(conn):
    try:
        if conn:
            db_pool.putconn(conn)
    except Exception as e:
        logging.error(f"Error releasing connection back to pool: {e}")

# Validate user_id input
def is_valid_user_id(user_id: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9_-]{1,50}$", user_id))

# Database helper functions
def get_permissions(user_id: str) -> List[str]:
    if not is_valid_user_id(user_id):
        logging.error("Invalid user ID format.")
        raise ValueError("Invalid user ID format.")

    conn = get_db_connection()
    permissions = []
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT permissions FROM permissions WHERE user_id = %s", (user_id,))
            result = cur.fetchone()
            if result:
                permissions = result[0].split(',')
        logging.info(f"Permissions retrieved for user {user_id}: {permissions}")
        return permissions
    except Exception as e:
        logging.error(f"Error retrieving permissions for user {user_id}: {e}")
        raise
    finally:
        if conn:
            release_db_connection(conn)

def set_permissions(user_id: str, permissions: List[str]):
    if not is_valid_user_id(user_id):
        
        logging.error("Invalid user ID format.")
        raise ValueError("Invalid user ID format.")

    permissions_str = ','.join(permissions)
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO permissions (user_id, permissions)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE SET permissions = EXCLUDED.permissions
            """, (user_id, permissions_str))
            conn.commit()
        logging.info(f"Permissions set for user {user_id}: {permissions}")
    except Exception as e:
        logging.error(f"Error setting permissions for user {user_id}: {e}")
        raise
    finally:
        if conn:
            release_db_connection(conn)

def validate_client_credentials(client_id: str, client_secret: str) -> bool:
    """
    Validates the client credentials against stored values.

    PROTOTYPE

    Args:
        client_id (str): The client ID provided by the client.
        client_secret (str): The client secret provided by the client.

    Returns:
        bool: True if credentials are valid, False otherwise.
    """
    # Replace with secure storage, e.g., a database or environment variable lookup
    stored_credentials = {
        "client_id_1": "client_secret_1",
        "client_id_2": "client_secret_2",
        "client_id_3": "client_secret_3",
    }

    # Check if the provided credentials match the stored credentials
    return stored_credentials.get(client_id) == client_secret

async def fire_and_forget_session_creation(user_id: str, permissions: List[str]) -> None:
    """
    Sends a fire-and-forget request to create a session in the session management service.

    Args:
        user_id (str): The user ID for the session.
        permissions (list[str]): List of permissions for the session.
    """
    mutation = """
    mutation CreateSession($userId: String!, $permissions: [String!]!) {
        createSession(userId: $userId, permissions: $permissions)
    }
    """
    variables = {"userId": user_id, "permissions": permissions}

    async with aiohttp.ClientSession() as session:
        try:
            # Fire-and-forget: Send the request
            async with session.post(
                f"{SESSION_API_URL}/session",
                json={"query": mutation, "variables": variables}
            ) as response:
                if response.status != 200:
                    print(f"Failed to initiate session creation for user_id: {user_id}. Status: {response.status}")
                else:
                    print(f"Fire-and-forget session creation initiated for user_id: {user_id}")
        except aiohttp.ClientError as e:
            print(f"Error sending fire-and-forget request: {e}")
        except Exception as e:
            print(f"Unexpected error during session creation: {e}")

