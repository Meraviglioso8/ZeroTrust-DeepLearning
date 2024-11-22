import os
import jwt
import datetime

from dotenv import load_dotenv
from starlette.applications import Starlette
from strawberry.asgi import GraphQL
import strawberry
from typing import Optional, List
from helper import *

load_dotenv()  # Load environment variables

# Define secret and algorithm for JWT
JWT_SECRET = os.getenv("JWT_SECRET", "your_secret_key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRES_MINUTES = 1  # Short-lived access tokens
REFRESH_TOKEN_EXPIRES_DAYS = 2    # Long-lived refresh tokens




# Define GraphQL PermissionsType
@strawberry.type
class PermissionsType:
    info: str
    permissions: list[str]


@strawberry.type
class PermissionsWithTokenType:
    info: str
    token: Optional[str] = None
    permissions: List[str]


# Utility to create JWT
def create_token(payload: dict, expires_delta: datetime.timedelta) -> str:
    payload["exp"] = datetime.datetime.utcnow() + expires_delta
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# Fire-and-Forget Session Creation



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
    def add_permission(self, user_id: str, permissions: list[str]) -> PermissionsType:
        try:
            # Fetch existing permissions for the user
            existing_permissions = get_permissions(user_id)
            if existing_permissions is None:
                existing_permissions = []

            # Add new permissions that are not already in the list
            for permission in permissions:
                if permission not in existing_permissions:
                    existing_permissions.append(permission)

            # Update permissions in the database
            set_permissions(user_id, existing_permissions)

            return PermissionsType(info="Permissions added successfully", permissions=existing_permissions)
        except Exception as e:
            print(f"Error adding permissions: {e}")
            return PermissionsType(info="Failed to add permissions", permissions=[])

    @strawberry.mutation
    async def authorization_code_grant(self, user_id: str) -> PermissionsWithTokenType:
        """
        Initiates the Authorization Code Grant process and responds immediately while session creation
        happens in the background.
        """
        try:
            # Fetch permissions for the user
            permissions = get_permissions(user_id)
            if not permissions:
                return PermissionsWithTokenType(
                    info="No permissions found for user",
                    permissions=[],
                    token=None
                )

            # Fire-and-forget session creation
            await fire_and_forget_session_creation(user_id, permissions)

            # Respond immediately to the client
            return PermissionsWithTokenType(
                info="Authorization initiated. Token generation is in progress.",
                permissions=permissions,
                token=None
            )
        except Exception as e:
            print(f"Error in authorization_code_grant: {e}")
            return PermissionsWithTokenType(
                info="Error during authorization",
                permissions=[],
                token=None
            )

    @strawberry.mutation
    async def client_credentials_flow(self, client_id: str, client_secret: str) -> PermissionsWithTokenType:
        """
        Handles the Client Credentials Flow to generate a JWT for service-to-service communication.
        """
        try:
            # Validate client credentials
            if not validate_client_credentials(client_id, client_secret):  # Implement this helper function
                return PermissionsWithTokenType(
                    info="Invalid client credentials",
                    permissions=[],
                    token=None
                )

            # Create short-lived token for the client
            access_token = create_token(
                {"client_id": client_id},
                expires_delta=datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRES_MINUTES)
            )

            return PermissionsWithTokenType(
                info="Client credentials authorization successful",
                permissions=[],
                token=access_token
            )
        except Exception as e:
            print(f"Error in client_credentials_flow: {e}")
            return PermissionsWithTokenType(
                info="Error during client credentials authorization",
                permissions=[],
                token=None
            )


# Create GraphQL schema
schema = strawberry.Schema(query=Query, mutation=Mutation)

# Starlette ASGI app setup
app = Starlette(debug=True)
graphql_app = GraphQL(schema)
app.add_route("/authorization", graphql_app)

# Main entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5002)
