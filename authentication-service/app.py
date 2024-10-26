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
    token: Optional[str] = None

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

            password_hash = generate_password_hash(password)
            totp_secret = generate_totp_secret()
            user_id = insert_user(email, password_hash, permissions, totp_secret)

            if user_id:
                return UserType(info="Signup Success")
            else:
                return UserType(info="Signup Failed")
        
        except Exception as e:
            # Log the error details here for debugging
            print(f"Error during signup: {e}")
            # Return a friendly message to the user
            return UserType(info="Try again later")

    @strawberry.mutation
    def login(self, email: str, password: str, totp_code: str) -> UserType:
        try:
            user = find_user_by_email(email)
            if not user:
                return UserType(info="User does not exist")

            user_id, user_email, stored_password_hash, user_permissions, secret_ref = user
            if not check_password_hash(stored_password_hash, password):
                return UserType(info="Invalid credentials")

            if not verify_totp(secret_ref, totp_code):
                return UserType(info="Invalid TOTP code")

            # Request the token from the authorization service
            token = request_token_from_authorization(user_id, user_permissions)

            if token:
                return UserType(info="Login Success", token=token)
            else:
                return UserType(info="Login failed: Unable to generate token")
        
        except Exception as e:
            # Log the error details here for debugging
            print(f"Error during login: {e}")
            # Return a friendly message to the user
            return UserType(info="Try again later")

# Create GraphQL schema
schema = strawberry.Schema(query=Query, mutation=Mutation)

# Starlette ASGI app setup
app = Starlette(debug=True)
graphql_app = GraphQL(schema)
app.add_route("/authentication", graphql_app)

# Main entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
