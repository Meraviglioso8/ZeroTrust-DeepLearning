import os
import jwt
import base64
import redis
import strawberry
from datetime import datetime, timedelta
from dotenv import load_dotenv
from strawberry.types import Info
from typing import Optional
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from strawberry.asgi import GraphQL

# Load environment variables from .env
load_dotenv()

# JWT secret and public keys
SECRET_KEY = str(os.getenv('SECRET_KEY'))
PUBLIC_KEY = str(os.getenv('PUBLIC_KEY'))
ADMIN_EMAIL = str(os.getenv('ADMIN'))

# Initialize Redis connection
redis_client = redis.StrictRedis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"), db=0, decode_responses=True)

# JWT Helper Functions
def generate_jwt_token(user_id: str, scopes: list, expiration_minutes=15):
    expiration_time = datetime.utcnow() + timedelta(minutes=expiration_minutes)
    payload = {
        "sub": user_id,
        "scopes": scopes,
        "exp": expiration_time
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_jwt_token(token: str):
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception("Token expired")
    except jwt.InvalidTokenError:
        raise Exception("Invalid token")

# Session Management Helper Functions
def generate_session_id():
    return base64.b64encode(os.urandom(24)).decode('utf-8')

def get_session(session_id: str):
    return redis_client.hgetall(session_id)

def set_session(session_id: str, access_token: str):
    expiration_time = timedelta(minutes=15)
    redis_client.hset(session_id, "access_token", access_token)
    redis_client.expire(session_id, expiration_time)

def delete_session(session_id: str):
    redis_client.delete(session_id)

# GraphQL Types and Mutations
@strawberry.type
class SessionResponse:
    info: str
    session_id: Optional[str] = None
    access_token: Optional[str] = None

@strawberry.type
class Query:
    @strawberry.field
    def validate_session(self, info: Info) -> SessionResponse:
        session_id = info.context['request'].cookies.get('session_id')
        if not session_id:
            return SessionResponse(info="Session ID not found", session_id=None)

        session_data = get_session(session_id)
        if session_data:
            access_token = session_data.get('access_token')
            try:
                verify_jwt_token(access_token)
                return SessionResponse(info="Session is valid", session_id=session_id)
            except Exception as e:
                return SessionResponse(info=f"Invalid session: {str(e)}", session_id=None)
        return SessionResponse(info="Session not found or expired", session_id=None)

@strawberry.type
class Mutation:
    @strawberry.mutation
    def login(self, email: str, password: str) -> SessionResponse:
        # Assume we validate the email and password via DB (not implemented here)
        user_id = email  # In practice, this would come from the database

        # Define user scopes based on their identity
        if email == ADMIN_EMAIL:
            scopes = ['blog_manage', 'product_manage']
        else:
            scopes = ['blog_read', 'blog_post', 'product_read']

        # Generate JWT and session ID
        access_token = generate_jwt_token(user_id, scopes)
        session_id = generate_session_id()

        # Store session in Redis
        set_session(session_id, access_token)

        # Return the session ID and JWT token
        return SessionResponse(info="Login successful", session_id=session_id, access_token=access_token)

    @strawberry.mutation
    def logout(self, session_id: str) -> SessionResponse:
        session_data = get_session(session_id)
        if session_data:
            delete_session(session_id)
            return SessionResponse(info="Session deleted", session_id=None)
        return SessionResponse(info="Session not found", session_id=None)

    @strawberry.mutation
    def validate_access_token(self, session_id: str) -> SessionResponse:
        session_data = get_session(session_id)
        if session_data:
            access_token = session_data.get('access_token')
            try:
                payload = verify_jwt_token(access_token)
                return SessionResponse(info="Access token valid", access_token=access_token)
            except Exception as e:
                return SessionResponse(info=f"Invalid token: {str(e)}", access_token=None)
        return SessionResponse(info="Session not found or expired", access_token=None)

# Create the GraphQL schema
schema = strawberry.Schema(query=Query, mutation=Mutation)

# Set up the Starlette ASGI app
app = Starlette(debug=True)
graphql_app = GraphQL(schema)
app.add_route("/graphql", graphql_app)

# Main entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
