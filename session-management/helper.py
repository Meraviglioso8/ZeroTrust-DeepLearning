import os
import jwt
import redis
import base64
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from typing import List

# Load environment variables from .env
load_dotenv()

# Redis connection details
redis_client = redis.StrictRedis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"), db=0, decode_responses=True)

# JWT secret key
SECRET_KEY = os.getenv('SECRET_KEY')

# Helper function to generate JWT token
def generate_access_token(user_id: str, permissions: List[str], expiration_minutes=15, issuer="zerotrust") -> str:
    try:
        # Define the token's issued, expiration, and 'not before' time
        issued_at = datetime.now(timezone.utc)
        expiration_time = issued_at + timedelta(minutes=expiration_minutes)
        not_before = issued_at  # Token is valid immediately upon issuance

        # Generate a unique identifier for the token to prevent replay attacks
        jwt_id = str(uuid.uuid4())

        # Construct payload with additional standard claims and unique ID
        payload = {
            "sub": user_id,
            "permissions": permissions,
            "iat": issued_at,
            "nbf": not_before,
            "exp": expiration_time,
            "iss": issuer,          # Token issuer for zero-trust verification
            "jti": jwt_id           # Unique token ID (JWT ID) for replay protection
        }

        # Encode token
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
            "iat": issued_at,
            "nbf": issued_at,
            "exp": expiration_time,
            "iss": issuer,
            "jti": jwt_id
        }

        refresh_token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        return refresh_token
    except Exception as e:
        print("Error generating refresh token:", e)
        return ""

# Session management function
def set_session(token: str) -> str:
    try:
        # Decode and verify token
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        
        # Ensure token's expiration and validity
        current_time = datetime.now(timezone.utc)
        if 'exp' in payload and datetime.fromtimestamp(payload['exp'], tz=timezone.utc) < current_time:
            raise ValueError("Token has expired")
        if 'nbf' in payload and datetime.fromtimestamp(payload['nbf'], tz=timezone.utc) > current_time:
            raise ValueError("Token is not yet valid")

        # Generate a secure session_id using a hash to prevent exposure
        raw_session_id = base64.b64encode(os.urandom(24)).decode('utf-8')
        session_id = hashlib.sha256(raw_session_id.encode()).hexdigest()

        # Store session with token in Redis, hashed and with restricted access
        redis_client.hset(session_id, "access_token", token)
        
        # Set session expiration to align with the token's expiration or max 15 mins
        session_duration = min(15, (payload['exp'] - int(current_time.timestamp())) // 60)
        redis_client.expire(session_id, timedelta(minutes=session_duration))

        return session_id
    except jwt.ExpiredSignatureError:
        print("Error: Token has expired.")
    except jwt.InvalidTokenError:
        print("Error: Invalid token.")
    except Exception as e:
        print(f"Error setting session: {e}")
    return ""