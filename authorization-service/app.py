import os
import jwt
import redis
import base64
from datetime import datetime, timedelta
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
            # Generate JWT token with the specified permissions and expiration
            token = generate_jwt_token(user_id, permissions, expiration_minutes)
            set_session(token)  # Store session in Redis
            return UserType(info="Token created successfully", token=token)

        except Exception as e:
            print(f"Error during token creation: {e}")
            return UserType(info="Failed to create token")

    @strawberry.mutation
    def add_permission(self, user_id: str, permission: str) -> PermissionsType:
        try:
            # Retrieve and update permissions for the user
            permissions = redis_client.hget(user_id, "permissions") or []
            if permission not in permissions:
                permissions.append(permission)
                redis_client.hset(user_id, "permissions", permissions)

            return PermissionsType(info="Permission added successfully", permissions=permissions)

        except Exception as e:
            print(f"Error adding permission: {e}")
            return PermissionsType(info="Failed to add permission")

    @strawberry.mutation
    def remove_permission(self, user_id: str, permission: str) -> PermissionsType:
        try:
            # Retrieve and update permissions for the user
            permissions = redis_client.hget(user_id, "permissions") or []
            if permission in permissions:
                permissions.remove(permission)
                redis_client.hset(user_id, "permissions", permissions)

            return PermissionsType(info="Permission removed successfully", permissions=permissions)

        except Exception as e:
            print(f"Error removing permission: {e}")
            return PermissionsType(info="Failed to remove permission")

# Create GraphQL schema
schema = strawberry.Schema(query=Query, mutation=Mutation)

# Starlette ASGI app setup
app = Starlette(debug=True)
graphql_app = GraphQL(schema)
app.add_route("/authorization", graphql_app)

# Main entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
