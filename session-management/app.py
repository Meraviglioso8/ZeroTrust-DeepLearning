import os
import jwt
import redis
import base64
import hashlib
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from starlette.applications import Starlette
from strawberry.asgi import GraphQL
import strawberry
from typing import Optional, List
from helper import *

# Define GraphQL UserType
@strawberry.type
class UserType:
    info: str
    token: Optional[str] = None

# Define GraphQL PermissionsType
@strawberry.type
class PermissionsType:
    info: str
    permissions: Optional[List[str]] = None

# Define GraphQL Queries
@strawberry.type
class Query:
    @strawberry.field
    def placeholder(self) -> str:
        return "This is a placeholder query."

# Define GraphQL Mutations
@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_token(self, user_id: str, permissions: List[str], expiration_minutes: int = 15) -> UserType:
        try:
            # Generate JWT access token with specified permissions and expiration
            token = generate_access_token(user_id, permissions, expiration_minutes)
            set_session(token, user_id)  # Store session in Redis
            return UserType(info="Token created successfully", token=token)

        except Exception as e:
            print(f"Error during token creation: {e}")
            return UserType(info="Failed to create token")

    @strawberry.mutation
    def add_permission(self, user_id: str, permission: str) -> PermissionsType:
        try:
            # Retrieve existing permissions, ensure permission is added
            permissions = redis_client.hget(user_id, "permissions")
            if permissions:
                permissions = permissions.split(',')
            else:
                permissions = []

            if permission not in permissions:
                permissions.append(permission)
                redis_client.hset(user_id, "permissions", ','.join(permissions))

            return PermissionsType(info="Permission added successfully", permissions=permissions)

        except Exception as e:
            print(f"Error adding permission: {e}")
            return PermissionsType(info="Failed to add permission")

    @strawberry.mutation
    def remove_permission(self, user_id: str, permission: str) -> PermissionsType:
        try:
            # Retrieve existing permissions, ensure permission is removed
            permissions = redis_client.hget(user_id, "permissions")
            if permissions:
                permissions = permissions.split(',')
                if permission in permissions:
                    permissions.remove(permission)
                    redis_client.hset(user_id, "permissions", ','.join(permissions))

            return PermissionsType(info="Permission removed successfully", permissions=permissions)

        except Exception as e:
            print(f"Error removing permission: {e}")
            return PermissionsType(info="Failed to remove permission")

    @strawberry.mutation
    def refresh_access_token(self, refresh_token: str) -> UserType:
        try:
            # Decode the refresh token
            payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=["HS256"])

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

            # Generate a new access token with a shorter expiration
            new_access_token = generate_access_token(user_id, permissions, expiration_minutes=15)
            
            # Optionally, update session with the new access token
            set_session(new_access_token, user_id)

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
app.add_route("/authorization", graphql_app)

# Session management function


# Main entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
