import os
import strawberry
from typing import Optional, Any
from starlette.applications import Starlette
from starlette.responses import RedirectResponse, JSONResponse
from starlette.middleware.cors import CORSMiddleware
from strawberry.asgi import GraphQL
from strawberry.permission import BasePermission
from strawberry.types import Info
from keycloak import KeycloakOpenID
import requests
import urllib3

# ─── Disable Insecure Warnings ─────────────────────────────────────────────────
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ─── Keycloak Configuration ────────────────────────────────────────────────────
KEYCLOAK_SERVER   = os.getenv("KEYCLOAK_SERVER")
REALM             = os.getenv("KEYCLOAK_REALM")
CLIENT_ID         = os.getenv("KEYCLOAK_CLIENT_ID")
CLIENT_SECRET     = os.getenv("KEYCLOAK_CLIENT_SECRET")
REDIRECT_URI      = os.getenv("REDIRECT_URI")
SPA_URL           = os.getenv("SPA_URL",           "http://localhost:6969")

kc = KeycloakOpenID(
    server_url        = KEYCLOAK_SERVER,
    realm_name        = REALM,
    client_id         = CLIENT_ID,
    client_secret_key = CLIENT_SECRET,
    verify            = False
)

# ─── Permission Class ─────────────────────────────────────────────────────────
class IsAuthenticated(BasePermission):
    message = "User is not authenticated"

    def has_permission(self, source: Any, info: Info, **kwargs) -> bool:
        user = info.context.get("user")
        return bool(user and user.get("active"))

# ─── GraphQL Types ─────────────────────────────────────────────────────────────
@strawberry.type
class TokenType:
    access_token: str
    refresh_token: Optional[str]
    id_token: Optional[str]
    expires_in: Optional[int]

# ─── Query & Mutation Definitions ──────────────────────────────────────────────
@strawberry.type
class Query:
    @strawberry.field
    def protected_data(self, info: Info) -> str:
        username = info.context["user"]["preferred_username"]
        return f"Hello, {username}! Your token is valid."

@strawberry.type
class Mutation:
    @strawberry.mutation
    def login_password(self, username: str, password: str) -> TokenType:
        tokens = kc.token(username=username, password=password)
        return TokenType(
            access_token = tokens["access_token"],
            refresh_token= tokens.get("refresh_token"),
            id_token     = tokens.get("id_token"),
            expires_in   = tokens.get("expires_in"),
        )

    @strawberry.mutation
    def refresh_token(self, refresh_token: str) -> TokenType:
        """
        Exchange an existing refresh_token for a new access_token.
        """
        new_tokens = kc.refresh_token(refresh_token)
        return TokenType(
            access_token = new_tokens["access_token"],
            refresh_token= new_tokens.get("refresh_token"),
            id_token     = new_tokens.get("id_token"),
            expires_in   = new_tokens.get("expires_in"),
        )

schema = strawberry.Schema(query=Query, mutation=Mutation)

# ─── Custom GraphQL App with Cookie Context ────────────────────────────────────
class AuthenticatedGraphQL(GraphQL):
    async def get_context(self, request, response):
        context = await super().get_context(request, response)
        token = request.cookies.get("access_token")
        if token:
            info = kc.introspect(token)
            context["user"] = info if info.get("active") else None
        return context

graphql_app = AuthenticatedGraphQL(schema)

# ─── Starlette App & Routes ────────────────────────────────────────────────────
app = Starlette(debug=True)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:6969"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_route("/graphql", graphql_app)
app.add_websocket_route("/graphql", graphql_app)

@app.route("/login")
async def login(request):
    return RedirectResponse(
        kc.auth_url(redirect_uri=REDIRECT_URI, scope="openid")
    )

@app.route("/callback")
async def callback(request):
    code = request.query_params.get("code")
    if not code:
        return JSONResponse({"error": "No code provided"}, status_code=400)
    tok = kc.token(
        grant_type   = "authorization_code",
        code         = code,
        redirect_uri = REDIRECT_URI
    )
    resp = RedirectResponse(SPA_URL)
    resp.set_cookie(
        "access_token",
        tok["access_token"],
        httponly=True,
        secure=True,
        samesite="none"
    )
    return resp

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
