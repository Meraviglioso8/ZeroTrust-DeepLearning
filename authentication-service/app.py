import strawberry
from helper import *
from werkzeug.security import check_password_hash, generate_password_hash
from typing import Optional
from starlette.applications import Starlette
from strawberry.asgi import GraphQL

# Define Roles and Permissions
ROLES = {
    "admin": ["manage_users", "manage_products", "view_orders", "process_orders"],
    "seller": ["manage_products", "view_orders"],
    "customer": ["view_products", "place_orders"],
}

PERMISSIONS = {
    "manage_users": ["create_user", "edit_user", "delete_user", "view_user"],
    "manage_products": ["add_product", "edit_product", "delete_product", "view_product"],
    "view_orders": ["list_orders", "view_order_details"],
    "process_orders": ["update_order_status", "ship_order", "cancel_order"],
    "view_products": ["list_products", "view_product_details"],
    "place_orders": ["create_order", "cancel_own_order"],
}

# Default role for signup
DEFAULT_ROLE = "customer"

# GraphQL Types and Mutations
@strawberry.type
class UserType:
    info: str
    token: Optional[str] = None
    qr_code: Optional[str] = None

@strawberry.type
class TokenType:
    info: str
    token: str
    permissions: Optional[str] = None

@strawberry.type
class Query:
    @strawberry.field
    def placeholder(self) -> str:
        return "This is a placeholder query."


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def signup(self, email: str, password: str) -> UserType:
        try:
            print(f"Starting signup process for email: {email}")

            # Check if the user already exists
            if await is_duplicate(email):
                return UserType(info="User already exists")

            # Generate hashed password and TOTP secret
            password_hash = generate_password_hash(password)
            totp_secret = await generate_totp_secret()

            # Assign the default role and permissions
            role = DEFAULT_ROLE
            permissions = ROLES[role]

            # Insert user into the database
            user_id = await insert_user(email, password_hash, totp_secret)
            if user_id:
                # Add permissions to the user
                await add_permissions_to_user(user_id, permissions)

                # Generate TOTP URI and QR code for Google Authenticator
                totp_uri = await generate_totp_uri(email, totp_secret)
                qr_code_base64 = await generate_qr_code(totp_uri)

                return UserType(info="Signup Success", qr_code=qr_code_base64)

            return UserType(info="Signup Failed")

        except Exception as e:
            print(f"Error during signup: {e}")
            return UserType(info="Try again later")

    @strawberry.mutation
    async def login(self, email: str, password: str, totp_code: str) -> UserType:
        """
        Handles user login by verifying credentials, TOTP, and initiating
        a fire-and-forget session creation request.

        Args:
            email (str): User's email address.
            password (str): User's plaintext password.
            totp_code (str): Time-based one-time password (TOTP) code.

        Returns:
            UserType: Object containing login status and token if successful.
        """
        try:
            # Use the process_authentication_fire_and_forget function directly
            response = await process_authentication_fire_and_forget(email, password, totp_code)

            # Convert the response from process_authentication_fire_and_forget into UserType
            return UserType(
                info=response.get("info", "An error occurred during login"),
                token=response.get("token")  # None if token is not present
            )

        except Exception as e:
            print(f"Unexpected error during login: {e}")
            return UserType(info="An error occurred during login", token=None)

    @strawberry.mutation
    async def get_qr_code(self, email: str) -> UserType:
        try:
            # Retrieve user and their TOTP secret
            user_id = await find_user_id_by_email(email)
            if not user_id:
                return UserType(info="User does not exist")

            # Fetch user role

            # Generate TOTP URI and QR code for Google Authenticator
            totp_secret = await query_secret_by_userid(user_id)
            totp_uri = await generate_totp_uri(email, totp_secret)
            qr_code_base64 = await generate_qr_code(totp_uri)

            return UserType(info="QR code generated successfully", qr_code=qr_code_base64)

        except Exception as e:
            print(f"Error generating QR code: {e}")
            return UserType(info="Failed to generate QR code")


# Create GraphQL schema
schema = strawberry.Schema(query=Query, mutation=Mutation)

# Starlette ASGI app setup
app = Starlette(debug=True)
graphql_app = GraphQL(schema)
app.add_route("/authentication", graphql_app)

# Main entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
