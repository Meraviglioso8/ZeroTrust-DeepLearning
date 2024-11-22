import asyncpg
import pyotp
import qrcode
import os
import base64
import aiohttp

from io import BytesIO
from barbicanclient import client
from keystoneauth1 import session
from keystoneauth1.identity import v3
from dotenv import load_dotenv
from typing import Optional, List
from werkzeug.security import check_password_hash

ROLES = {
    "admin": ["manage_users", "manage_products", "view_orders", "process_orders"],
    "seller": ["manage_products", "view_orders"],
    "customer": ["view_products", "place_orders"],
}

PERMISSIONS = {
    "manage_users": ["create_user", "edit_user", "delete_user", "view_user"],
    "manage_products": ["add_product", "edit_product", "delete_product", "view_product"],
    "view_orders": ["list_orders", "view_order_details"],
    "process_orders": ["update_order_status", "ship_order", "cancel_order"],
    "view_products": ["list_products", "view_product_details"],
    "place_orders": ["create_order", "cancel_own_order"],
}
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



# Helper Functions
def can_user_perform_action(user_role: str, action: str) -> bool:
    """
    Checks if a user with a specific role can perform a given action.

    Args:
        user_role (str): The role of the user (e.g., "admin", "seller").
        action (str): The action to check (e.g., "create_order").

    Returns:
        bool: True if the role allows the action, False otherwise.
    """
    permissions = ROLES.get(user_role, [])
    for permission in permissions:
        allowed_actions = PERMISSIONS.get(permission, [])
        if action in allowed_actions:
            return True
    return False

async def get_permissions_of_user(user_id: str) -> Optional[dict]:
    """
    Retrieves the permissions of a user by their user ID using a GraphQL query.

    Args:
        user_id (str): The ID of the user.

    Returns:
        Optional[dict]: A dictionary containing the user's permissions or None if an error occurs.
    """
    query = """
    query GetPermissions($userId: String!) {
        getPermissions(userId: $userId) {
            permissions
        }
    }
    """
    variables = {
        "userId": str(user_id),
    }

    try:
        # Send the request
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{AUTHORIZATION_API_URL}/authorization",
                json={"query": query, "variables": variables}
            ) as response:
                response.raise_for_status()
                result = await response.json()
                return result.get("data", {}).get("getPermissions", {})
    except aiohttp.ClientError as e:
        print(f"Error sending GraphQL query to get permissions: {e}")
        return None



async def release_db_connection(conn):
    """
    Releases the database connection, closing it if necessary.

    Args:
        conn: The psycopg2 database connection object.
    """
    try:
        if conn:
            conn.close()  # Close the connection
            print("Database connection released.")
    except Exception as e:
        print(f"Error releasing database connection: {e}")

# Function to establish a database connection
async def get_db_connection():
    """Establish a database connection."""
    try:
        conn = await asyncpg.connect(
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            database=POSTGRES_DB,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
        )
        return conn
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        return None


# Function to close the database connection
async def release_db_connection(conn):
    """Releases the database connection."""
    try:
        if conn:
            await conn.close()
            print("Database connection released.")
    except Exception as e:
        print(f"Error releasing database connection: {e}")


# Check if an email is a duplicate
async def is_duplicate(email: str) -> bool:
    conn = await get_db_connection()
    if conn:
        try:
            result = await conn.fetchval(
                "SELECT email FROM users WHERE email = $1", email
            )
            return result is not None
        finally:
            await release_db_connection(conn)


# Retrieve a user's hashed password by email
async def find_user_hashed_password_by_email(email: str) -> Optional[str]:
    conn = await get_db_connection()
    if conn:
        try:
            result = await conn.fetchval(
                "SELECT password FROM users WHERE email = $1", email
            )
            return result
        finally:
            await release_db_connection(conn)


# Retrieve a user's ID by email
async def find_user_id_by_email(email: str) -> Optional[int]:
    conn = await get_db_connection()
    if conn:
        try:
            result = await conn.fetchval(
                "SELECT id FROM users WHERE email = $1", email
            )
            return result
        finally:
            await release_db_connection(conn)


# Insert a new user into the database
async def insert_user(email: str, password_hash: str, totp_secret: str) -> Optional[int]:
    conn = await get_db_connection()
    if conn:
        try:
            result = await conn.fetchval(
                "INSERT INTO users (email, password) VALUES ($1, $2) RETURNING id",
                email,
                password_hash,
            )
            # Store TOTP secret after inserting the user
            await store_secret_in_barbican(result, totp_secret)
            return result
        finally:
            await release_db_connection(conn)

async def store_secret_in_barbican(userid: str, secret: str):
    try:
        new_secret = barbican.secrets.create()
        new_secret.name = f'Random plain text password for user {userid}'
        new_secret.payload = secret
        new_secret.store()
    except Exception as e:
        print(f"Error storing secret in Barbican: {e}")


# Generate a TOTP URI
async def generate_totp_uri(email, totp_secret):
    issuer_name = "ZERO-TRUST"
    return f"otpauth://totp/{issuer_name}:{email}?secret={totp_secret}&issuer={issuer_name}"


# Generate a QR code
async def generate_qr_code(uri):
    qr = qrcode.make(uri)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return qr_base64

async def verify_totp(email: str, totp_code: str) -> bool:
    user_id = await find_user_id_by_email(email)
    totp_secret = await query_secret_by_userid(user_id)
    if not totp_secret:
        return False
    totp = pyotp.TOTP(totp_secret)
    return totp.verify(totp_code)

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
# Generate a TOTP secret
async def generate_totp_secret():
    return pyotp.random_base32()

# Call the authorization service to request token generation
async def add_permissions_to_user(user_id: str, permissions: List[str]) -> Optional[dict]:
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


async def process_authentication_fire_and_forget(email: str, password: str, totp_code: str) -> dict:
    """
    Authenticate the user and send a session creation request to the session management service
    without waiting for its response.

    Args:
        email (str): User email.
        password (str): User password.
        totp_code (str): User's TOTP code.

    Returns:
        dict: Response to the client indicating authentication status.
    """
    mutation = """
    mutation AuthorizationCodeGrant($userId: String!) {
        authorizationCodeGrant(userId: $userId) {
            info
            token
            permissions
        }
    }
    """
    try:
        # Step 1: Validate user credentials
        stored_password_hash = await find_user_hashed_password_by_email(email)
        if not stored_password_hash:
            return {"info": "User does not exist"}

        # Verify password
        if not check_password_hash(stored_password_hash, password):
            return {"info": "Invalid credentials"}

        # Verify TOTP code
        if not await verify_totp(email, totp_code):
            return {"info": "Invalid TOTP code"}

        # Retrieve user ID
        user_id = await find_user_id_by_email(email)
        if not user_id:
            return {"info": "User ID not found"}

        # Step 2: Fire-and-forget session creation
        variables = {"userId": str(user_id)}
        async with aiohttp.ClientSession() as session:
            try:
                # Fire-and-forget request with proper await
                await session.post(
                    f"{AUTHORIZATION_API_URL}/authorization",
                    json={"query": mutation, "variables": variables}
                )
                print(f"Fire-and-forget session creation initiated for user_id: {user_id}")
            except aiohttp.ClientError as e:
                print(f"Error sending session creation request: {e}")
            except Exception as e:
                print(f"Unexpected error during session creation: {e}")

        # Step 3: Respond to the client immediately
        return {
            "info": "Authentication successful. Token is being generated.",
            "user_id": user_id
        }

    except Exception as e:
        print(f"Unexpected error during authentication: {e}")
        return {"info": "An error occurred during authentication"}

