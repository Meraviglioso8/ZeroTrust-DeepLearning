import strawberry
from helper import *
from werkzeug.security import check_password_hash, generate_password_hash
from typing import Optional, List
from starlette.applications import Starlette
from strawberry.asgi import GraphQL

# GraphQL Types and Mutations
@strawberry.type
class UserType:
    info: str
    qr_code: str

@strawberry.type
class Query:
    @strawberry.field
    def placeholder(self) -> str:
        return "This is a placeholder query."

@strawberry.type
class Mutation:
    @strawberry.mutation
    def signup(self, email: str, password: str, permissions: List[str]) -> UserType:
        try:
            if is_duplicate(email):
                return UserType(info="User already exists")

            # Generate hashed password and TOTP secret
            password_hash = generate_password_hash(password)
            totp_secret = generate_totp_secret()
            
            # Insert user into the database
            user_id = insert_user(email, password_hash, permissions, totp_secret)

            if user_id:
                # Generate TOTP URI and QR code for Google Authenticator
                totp_uri = generate_totp_uri(email, totp_secret)
                qr_code_base64 = generate_qr_code(totp_uri)
                
                # Return signup success message along with QR code
                return UserType(info="Signup Success", qr_code=qr_code_base64)
            else:
                return UserType(info="Signup Failed")
        
        except Exception as e:
            print(f"Error during signup: {e}")
            return UserType(info="Try again later")


    @strawberry.mutation
    def login(self, email: str, password: str, totp_code: str) -> UserType:
        try:
            # Retrieve only necessary information for login
            user_data = find_user_by_email(email)
            if not user_data:
                return UserType(info="User does not exist")

            # Unpack only the required fields: id, email, password hash, and TOTP secret
            user_id, stored_password_hash, totp_secret = user_data

            # Verify password
            if not check_password_hash(stored_password_hash, password):
                return UserType(info="Invalid credentials")

            # Verify TOTP code
            if not verify_totp(totp_secret, totp_code):
                return UserType(info="Invalid TOTP code")

            # Request the token from the authorization service with minimal data
            token = request_token_from_authorization(user_id)

            if token:
                return UserType(info="Login Success", token=token)
            else:
                return UserType(info="Login failed: Unable to generate token")
        
        except Exception as e:
            # Log the error details here for debugging
            print(f"Error during login: {e}")
            return UserType(info="Try again later")

    @strawberry.mutation
    def get_qr_code(self, email: str) -> UserType:
        try:
            # Find user and retrieve TOTP secret
            user = find_user_by_email(email)
            if not user:
                return UserType(info="User does not exist")

            user_id, user_email, stored_password_hash, user_permissions, totp_secret = user
            
            # Generate the TOTP URI and QR code for Google Authenticator
            totp_uri = generate_totp_uri(user_email, totp_secret)
            qr_code_base64 = generate_qr_code(totp_uri)
            
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
