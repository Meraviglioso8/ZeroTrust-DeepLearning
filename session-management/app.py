import os
import jwt
import redis
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from starlette.applications import Starlette
from strawberry.asgi import GraphQL
import strawberry
from typing import Optional, List
import asyncio
from helper import *

# Load environment variables
load_dotenv()

# Redis setup
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# JWT configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key")
ALGORITHM = "HS256"  # Default to HS256 if not specified


# Define GraphQL UserType
@strawberry.type
class UserType:
    info: str
    token: Optional[str] = None

# Define GraphQL Queries
@strawberry.type
class Query:
    @strawberry.field
    def get_session_token(self, user_id: str) -> UserType:
        """
        Fetch the token and session details for a user.
        """
        session_data = redis_client.hgetall(user_id)
        if not session_data:
            return UserType(info="Session not found")
        return UserType(info="Session retrieved successfully", token=session_data.get("access_token"))
    

# Define GraphQL Mutations
@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_session(self, user_id: str, permissions: List[str]) -> str:
        """
        Asynchronously create a session for a user.
        """
        asyncio.create_task(generate_and_notify_session(user_id, permissions))
        return "Session creation initiated."

    @strawberry.mutation
    def refresh_access_token(self, refresh_token: str) -> UserType:
        """
        Refresh the access token using a refresh token.
        """
        try:
            # Decode the refresh token
            payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])

            # Check expiration
            current_time = datetime.now(timezone.utc)
            expiration_time = datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
            if expiration_time < current_time:
                raise ValueError("Refresh token has expired")

            # Retrieve user ID and permissions from the refresh token payload
            user_id = payload["sub"]
            permissions = redis_client.hget(user_id, "permissions")
            if permissions:
                permissions = permissions.split(',')
            else:
                return UserType(info="No permissions found")

            # Generate a new access token
            new_access_token = generate_access_token(user_id, permissions)

            # Update session with the new access token
            asyncio.create_task(set_session_fire_and_forget(new_access_token, lambda t: None))

            return UserType(info="Access token refreshed successfully", token=new_access_token)

        except jwt.ExpiredSignatureError:
            print("Error: Refresh token has expired.")
            return UserType(info="Failed to refresh access token: Refresh token expired")
        except jwt.InvalidTokenError:
            print("Error: Invalid refresh token.")
            return UserType(info="Failed to refresh access token: Invalid refresh token")
        except Exception as e:
            print(f"Error refreshing access token: {e}")
            return UserType(info="Failed to refresh access token")


# Create GraphQL schema
schema = strawberry.Schema(query=Query, mutation=Mutation)

# Starlette ASGI app setup
app = Starlette(debug=True)
graphql_app = GraphQL(schema)
app.add_route("/session", graphql_app)

# Main entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5003)
