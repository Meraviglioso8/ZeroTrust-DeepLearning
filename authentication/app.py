import os
import jwt
import psycopg2
import strawberry
import pyotp  # For TOTP (Google Authenticator)
import qrcode  # For generating QR codes
import io
from datetime import datetime, timedelta
from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash
from strawberry.types import Info
from typing import Optional, List
from starlette.applications import Starlette
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route
from strawberry.asgi import GraphQL

# Load environment variables
load_dotenv()

# PostgreSQL connection details
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
POSTGRES_DB = os.getenv('POSTGRES_DB')
POSTGRES_HOST = os.getenv('POSTGRES_HOST')
POSTGRES_PORT = os.getenv('POSTGRES_PORT')

# JWT secret key
SECRET_KEY = os.getenv('SECRET_KEY')

# Connect to PostgreSQL
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

# Helper functions
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
    query = "SELECT id, email, password, totp_secret, permissions FROM users WHERE email = %s"
    cursor.execute(query, (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def insert_user(email: str, password_hash: str, totp_secret: str, permissions: List[str]):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "INSERT INTO users (email, password, totp_secret, permissions) VALUES (%s, %s, %s, %s) RETURNING id"
    cursor.execute(query, (email, password_hash, totp_secret, permissions))
    conn.commit()
    user_id = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return user_id

def generate_token(user_id: str, permissions: List[str], expiration_minutes: int = 15):
    expiration_time = datetime.utcnow() + timedelta(minutes=expiration_minutes)
    payload = {
        'id': user_id,
        'permissions': permissions,  # Attach permissions to the token
        'exp': expiration_time
    }
    token = jwt.encode(payload=payload, key=SECRET_KEY, algorithm='HS256')
    return token

# TOTP Functions
def generate_totp_secret():
    return pyotp.random_base32()  # Generates a random TOTP secret key

def generate_totp_qr_code(email: str, totp_secret: str):
    totp_uri = pyotp.totp.TOTP(totp_secret).provisioning_uri(name=email, issuer_name="MyApp")
    qr = qrcode.make(totp_uri)
    buffer = io.BytesIO()
    qr.save(buffer)
    buffer.seek(0)
    return buffer

def verify_totp(totp_secret: str, totp_code: str):
    totp = pyotp.TOTP(totp_secret)
    return totp.verify(totp_code)

# Function-based access check
def has_permission(info: Info, required_permission: str) -> bool:
    auth_header = info.context['request'].headers.get("Authorization")
    if not auth_header:
        return False
    
    token = auth_header.split("Bearer ")[1]
    try:
        decoded_token = jwt.decode(token, key=SECRET_KEY, algorithms=['HS256'])
        user_permissions = decoded_token.get("permissions", [])
        return required_permission in user_permissions
    except jwt.ExpiredSignatureError:
        return False
    except jwt.InvalidTokenError:
        return False

# Define GraphQL types and mutations using Strawberry
@strawberry.type
class UserType:
    info: str
    session_id: Optional[str] = None
    qr_code_url: Optional[str] = None  # New field to return QR code during signup

@strawberry.type
class Query:
    @strawberry.field
    def validate_session(self, info: Info) -> UserType:
        # No permission required for this function
        session_id = info.context['request'].headers.get("Authorization")
        if not session_id:
            return UserType(info="Session ID not found")

        # Validate JWT token and return user status
        try:
            token = session_id.split("Bearer ")[1]
            jwt.decode(token, key=SECRET_KEY, algorithms=['HS256'])
            return UserType(info="User is logged in")
        except jwt.ExpiredSignatureError:
            return UserType(info="Session expired")
        except jwt.InvalidTokenError:
            return UserType(info="Invalid token")

    @strawberry.field
    def protected_admin_query(self, info: Info) -> UserType:
        # Function-based access control: requires specific permission to access
        if not has_permission(info, required_permission="can_access_admin_query"):
            return UserType(info="Access denied: Permission required")
        return UserType(info="Admin data access granted")

    @strawberry.field
    def protected_user_query(self, info: Info) -> UserType:
        # Function-based access control: requires specific permission to access
        if not has_permission(info, required_permission="can_access_user_query"):
            return UserType(info="Access denied: Permission required")
        return UserType(info="User data access granted")

@strawberry.type
class Mutation:
    @strawberry.mutation
    def signup(self, email: str, password: str, permissions: List[str]) -> UserType:
        if is_duplicate(email):
            return UserType(info="User already exists")

        password_hash = generate_password_hash(password)
        totp_secret = generate_totp_secret()  # Generate TOTP secret
        user_id = insert_user(email, password_hash, totp_secret, permissions)

        if user_id:
            qr_code_buffer = generate_totp_qr_code(email, totp_secret)
            qr_code_url = f"/qr-code/{user_id}"  # Expose this QR code via a route
            return UserType(info="Signup Success", qr_code_url=qr_code_url)
        return UserType(info="Signup Failed")

    @strawberry.mutation
    def login(self, email: str, password: str, totp_code: str) -> UserType:
        user = find_user_by_email(email)
        if not user:
            return UserType(info="User does not exist")

        user_id, user_email, stored_password_hash, totp_secret, user_permissions = user
        if not check_password_hash(stored_password_hash, password):
            return UserType(info="Invalid credentials")

        # Verify TOTP code
        if not verify_totp(totp_secret, totp_code):
            return UserType(info="Invalid TOTP code")

        # Generate a token with the user's permissions
        token = generate_token(user_id, user_permissions)
        return UserType(info="Login Success", session_id=token)

# Create the Strawberry GraphQL schema
schema = strawberry.Schema(query=Query, mutation=Mutation)

# QR Code Route
async def serve_qr_code(request):
    user_id = request.path_params['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT totp_secret, email FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user:
        totp_secret, email = user
        qr_code_buffer = generate_totp_qr_code(email, totp_secret)
        return StreamingResponse(qr_code_buffer, media_type="image/png")
    return JSONResponse({"error": "User not found"}, status_code=404)

# Create a Starlette ASGI app with the Strawberry GraphQL endpoint and QR code route
app = Starlette(debug=True, routes=[
    Route("/qr-code/{user_id}", serve_qr_code),  # Serve QR code for TOTP setup
])
graphql_app = GraphQL(schema)
app.add_route("/graphql", graphql_app)

# Main entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
