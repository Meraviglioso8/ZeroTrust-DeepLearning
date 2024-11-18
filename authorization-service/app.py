import os
import psycopg2
from dotenv import load_dotenv
from starlette.applications import Starlette
from strawberry.asgi import GraphQL
import strawberry
from typing import Optional, List
from helper import *

# Define GraphQL PermissionsType
@strawberry.type
class PermissionsType:
    info: str
    permissions: list[str]  # Updated to handle a list of permissions

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
            print(existing_permissions)

            if existing_permissions is None:
                existing_permissions = []  # Initialize if no permissions exist

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
    def remove_permissions(self, user_id: str, permissions: List[str]) -> PermissionsType:
        try:
            # Fetch existing permissions for the user
            existing_permissions = get_permissions(user_id)
            print(existing_permissions)

            if existing_permissions is None:
                return PermissionsType(info="No permissions to remove", permissions=[])

            # Remove specified permissions
            updated_permissions = [perm for perm in existing_permissions if perm not in permissions]

            # Update permissions in the database
            set_permissions(user_id, updated_permissions)

            return PermissionsType(info="Permissions removed successfully", permissions=updated_permissions)
        except Exception as e:
            print(f"Error removing permissions: {e}")
            return PermissionsType(info="Failed to remove permissions", permissions=[])
        
    @strawberry.mutation
    def change_permissions(self, user_id: str, new_permissions: List[str]) -> PermissionsType:
        try:
            # Update permissions in the database
            set_permissions(user_id, new_permissions)
            return PermissionsType(info="Permissions updated successfully", permissions=new_permissions)
        except Exception as e:
            print(f"Error updating permissions: {e}")
            return PermissionsType(info="Failed to update permissions", permissions=[])



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
