import os
import strawberry
from typing import List, Optional, Any
from starlette.applications import Starlette
from starlette.responses import RedirectResponse, JSONResponse, HTMLResponse
from starlette.middleware.cors import CORSMiddleware
from strawberry.asgi import GraphQL
from strawberry.permission import BasePermission
from strawberry.types import Info
from starlette.requests import Request
from keycloak import KeycloakOpenID
from keycloak.exceptions import KeycloakPostError
from dotenv import load_dotenv
import requests

# ─── Env & Keycloak setup ─────────────────────────────────────────────────────
load_dotenv()
KEYCLOAK_SERVER   = os.getenv("KEYCLOAK_SERVER")     
REALM             = os.getenv("KEYCLOAK_REALM")      
CLIENT_ID         = os.getenv("KEYCLOAK_CLIENT_ID")   
CLIENT_SECRET     = os.getenv("KEYCLOAK_CLIENT_SECRET")
REDIRECT_URI      = os.getenv("REDIRECT_URI")       

PRODUCT_SERVICE_URL   = "http://localhost:5002/graphql"  

_raw = os.getenv("PRODUCT_SERVICE_URL") or "http://localhost:5002"
BASE_URL = _raw.rstrip("/"  )

kc = KeycloakOpenID(
    server_url        = KEYCLOAK_SERVER,
    realm_name        = REALM,
    client_id         = CLIENT_ID,
    client_secret_key = CLIENT_SECRET,
    verify            = False,
)

REVOCATION_URL = f"{KEYCLOAK_SERVER}/realms/{REALM}/protocol/openid-connect/revoke"

# ─── Permission Class ─────────────────────────────────────────────────────────
class IsAuthenticated(BasePermission):
    message = "User is not authenticated"
    def has_permission(self, source: Any, info: Info, **kwargs) -> bool:
        u = info.context.get("user")
        return bool(u and u.get("active"))

# ─── GraphQL types & schema (for GraphiQL if you wish) ───────────────────────
@strawberry.type
class TokenType:
    access_token: str
    refresh_token: Optional[str]
    id_token: Optional[str]
    expires_in: Optional[int]

@strawberry.type
class ProductType:
    id: int
    name: str
    description: str
    price: float

@strawberry.type
class Query:
    @strawberry.field(permission_classes=[IsAuthenticated])
    def all_products(self, info: Info) -> List[ProductType]:
        ...  # only needed if you expose /graphql for IDE

    @strawberry.field
    def protected_data(self, info: Info) -> str:
        ...

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
        new_tokens = kc.refresh_token(refresh_token)
        return TokenType(
            access_token = new_tokens["access_token"],
            refresh_token= new_tokens.get("refresh_token"),
            id_token     = new_tokens.get("id_token"),
            expires_in   = new_tokens.get("expires_in"),
        )

schema = strawberry.Schema(query=Query, mutation=Mutation)

class AuthenticatedGraphQL(GraphQL):
    async def get_context(self, request: Request, response):
        ctx = await super().get_context(request, response)
        token = request.cookies.get("access_token")
        if token:
            info = kc.introspect(token)
            ctx["user"] = info if info.get("active") else None
        else:
            ctx["user"] = None
        ctx["request"] = request
        return ctx

graphql_app = AuthenticatedGraphQL(
    schema,
    graphql_ide=True,
    allow_queries_via_get=True,
)

# ─── Starlette App & Routes ────────────────────────────────────────────────────
app = Starlette(debug=True)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.route("/")
async def root(request: Request):
    return RedirectResponse("/products" if request.cookies.get("access_token") else "/login")

@app.route("/login")
async def login(request: Request):
    return RedirectResponse(
        kc.auth_url(redirect_uri=REDIRECT_URI, scope="openid")
    )

@app.route("/callback")
async def callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return JSONResponse({"error":"No code provided"}, status_code=400)

    tok = kc.token(
        grant_type   = "authorization_code",
        code         = code,
        redirect_uri = REDIRECT_URI,
    )

    resp = RedirectResponse("/products")
    resp.set_cookie("access_token",  tok["access_token"],  httponly=True, secure=True, samesite="none")
    if "refresh_token" in tok:
        resp.set_cookie("refresh_token", tok["refresh_token"], httponly=True, secure=True, samesite="none")
    return resp

@app.route("/products")
async def products(request: Request):
    # 1) Grab the old tokens from cookies
    old_at = request.cookies.get("access_token")
    old_rt = request.cookies.get("refresh_token")
    if not old_at or not old_rt:
        return RedirectResponse("/login")

    # 2) Rotate refresh → get new AT/RT
    try:
        new_tok = kc.refresh_token(old_rt)
    except KeycloakPostError:
        # invalid refresh → force re-login
        resp = RedirectResponse("/login")
        resp.delete_cookie("access_token")
        resp.delete_cookie("refresh_token")
        return resp

    new_at = new_tok["access_token"]
    new_rt = new_tok.get("refresh_token", old_rt)

    # 3) Revoke the old access token in Keycloak
    requests.post(
        REVOCATION_URL,
        data={
            "token": old_at,
            "token_type_hint": "access_token",
        },
        auth=(CLIENT_ID, CLIENT_SECRET),                # ensure this matches your KeycloakOpenID param
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        verify=False,
    )

    # 4) Proxy the GET to your product service
    proxy_url = f"{BASE_URL}/products"
    print(f"[products] fetching --> {proxy_url}?{dict(request.query_params)}")
    try:
        svc_resp = requests.get(proxy_url, params=request.query_params, timeout=5)
        svc_resp.raise_for_status()
    except requests.HTTPError as err:
        print(f"[products] upstream error: {err.response.status_code} {err.response.text}")
        return HTMLResponse(
            f"<h1>Product service error</h1>"
            f"<p>Status: {err.response.status_code}</p>",
            status_code=502
        )

    html = svc_resp.text

    # 5) Return the proxied HTML and set the *new* cookies
    response = HTMLResponse(html)
    response.set_cookie("access_token",  new_at, httponly=True, secure=True, samesite="none")
    response.set_cookie("refresh_token", new_rt, httponly=True, secure=True, samesite="none")
    return response


# expose GraphQL/GraphiQL if desired
app.add_route("/graphql", graphql_app)
app.add_websocket_route("/graphql", graphql_app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
