import os
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
from typing import List
import re
import logging

# Load environment variables
load_dotenv()

# PostgreSQL connection details
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
POSTGRES_DB = os.getenv('POSTGRES_DB')
POSTGRES_HOST = os.getenv('POSTGRES_HOST')
POSTGRES_PORT = os.getenv('POSTGRES_PORT')

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

print(get_permissions('13'))
