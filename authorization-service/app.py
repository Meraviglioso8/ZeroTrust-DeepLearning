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
    def add_permission(self, user_id: str, permission: str) -> PermissionsType:
        try:
            permissions = get_permissions(user_id)
            if permission not in permissions:
                permissions.append(permission)
                set_permissions(user_id, permissions)

            return PermissionsType(info="Permission added successfully", permissions=permissions)
        except Exception as e:
            print(f"Error adding permission: {e}")
            return PermissionsType(info="Failed to add permission")

    @strawberry.mutation
    def remove_permission(self, user_id: str, permission: str) -> PermissionsType:
        try:
            permissions = get_permissions(user_id)
            if permission in permissions:
                permissions.remove(permission)
                set_permissions(user_id, permissions)

            return PermissionsType(info="Permission removed successfully", permissions=permissions)
        except Exception as e:
            print(f"Error removing permission: {e}")
            return PermissionsType(info="Failed to remove permission")

    @strawberry.mutation
    def change_permissions(self, user_id: str, new_permissions: List[str]) -> PermissionsType:
        try:
            set_permissions(user_id, new_permissions)
            return PermissionsType(info="Permissions updated successfully", permissions=new_permissions)
        except Exception as e:
            print(f"Error updating permissions: {e}")
            return PermissionsType(info="Failed to update permissions")

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
