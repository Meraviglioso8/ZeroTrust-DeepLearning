import os
import jwt
import redis
import base64
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from typing import List
import asyncio

# Load environment variables from .env
load_dotenv()

# Redis connection details
redis_client = redis.StrictRedis(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0,
    decode_responses=True
)

# JWT secret key
SECRET_KEY = os.getenv('SECRET_KEY')

async def generate_and_notify_session(user_id: str, permissions: List[str]):
    try:
        token = generate_access_token(user_id, permissions)
        redis_client.hset(user_id, mapping={"access_token": token, "permissions": ','.join(permissions)})
        print(f"Session created for user {user_id} with token: {token}")
    except Exception as e:
        print(f"Error creating session for user {user_id}: {e}")

# Helper function to generate JWT token
def generate_access_token(user_id: str, permissions: List[str], expiration_minutes=15, issuer="zerotrust") -> str:
    try:
        issued_at = datetime.now(timezone.utc)
        expiration_time = issued_at + timedelta(minutes=expiration_minutes)
        jwt_id = str(uuid.uuid4())

        payload = {
            "sub": user_id,
            "permissions": permissions,
            "iat": issued_at.timestamp(),
            "nbf": issued_at.timestamp(),
            "exp": expiration_time.timestamp(),
            "iss": issuer,
            "jti": jwt_id
        }

        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        return token
    except Exception as e:
        print("Error generating access token:", e)
        return ""

def generate_refresh_token(user_id: str, expiration_days=7, issuer="zerotrust") -> str:
    try:
        issued_at = datetime.now(timezone.utc)
        expiration_time = issued_at + timedelta(days=expiration_days)
        jwt_id = str(uuid.uuid4())

        payload = {
            "sub": user_id,
            "iat": issued_at.timestamp(),
            "nbf": issued_at.timestamp(),
            "exp": expiration_time.timestamp(),
            "iss": issuer,
            "jti": jwt_id
        }

        refresh_token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        return refresh_token
    except Exception as e:
        print("Error generating refresh token:", e)
        return ""

# Session management function
async def set_session_fire_and_forget(token: str, end_user_callback: callable) -> None:
    """
    Asynchronously set the session and notify the end user (fire-and-forget).
    
    Args:
        token (str): The JWT access token.
        end_user_callback (callable): A function to notify the end user with the token.
    """
    try:
        # Decode and verify token
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])

        # Ensure token's validity period
        current_time = datetime.now(timezone.utc)
        expiration_time = datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
        not_before_time = datetime.fromtimestamp(payload['nbf'], tz=timezone.utc)

        if expiration_time < current_time:
            raise ValueError("Token has expired")
        if not_before_time > current_time:
            raise ValueError("Token is not yet valid")

        # Generate a secure session_id
        raw_session_id = base64.b64encode(os.urandom(24)).decode('utf-8')
        session_id = hashlib.sha256(raw_session_id.encode()).hexdigest()

        # Store session in Redis
        redis_client.hset(session_id, mapping={
            "access_token": token,
            "user_id": payload.get("sub"),
            "permissions": ','.join(payload.get("permissions", [])),
            "expires_at": expiration_time.isoformat()
        })

        # Set Redis expiration based on token expiration
        session_duration = max(1, (expiration_time - current_time).seconds)
        redis_client.expire(session_id, session_duration)

        # Notify the end user (asynchronous, fire-and-forget)
        await asyncio.create_task(end_user_callback(token))

    except jwt.ExpiredSignatureError:
        print("Error: Token has expired.")
    except jwt.InvalidTokenError:
        print("Error: Invalid token.")
    except Exception as e:
        print(f"Error setting session: {e}")


# Example end-user notification function
async def notify_end_user(token: str) -> None:
    """
    Simulate notifying the end user with the token.

    Args:
        token (str): The JWT token to send to the end user.
    """
    try:
        print(f"Sending token to end user: {token}")
        # Simulate a network call or other asynchronous operation
        await asyncio.sleep(1)
    except Exception as e:
        print(f"Error notifying end user: {e}")

