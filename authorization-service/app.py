import os
import jwt
import redis
import base64
from datetime import datetime, timedelta
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

# Load environment variables from .env
load_dotenv()

# Redis connection details
redis_client = redis.StrictRedis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"), db=0, decode_responses=True)

# JWT secret and public keys
SECRET_KEY = os.getenv('SECRET_KEY')

# Helper function to generate JWT token
def generate_jwt_token(user_id: str, permissions: list, expiration_minutes=15):
    expiration_time = datetime.utcnow() + timedelta(minutes=expiration_minutes)
    payload = {
        "sub": user_id,
        "permissions": permissions,
        "exp": expiration_time
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

# Session management
def set_session(token: str):
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    session_id = base64.b64encode(os.urandom(24)).decode('utf-8')
    redis_client.hset(session_id, "access_token", token)
    redis_client.expire(session_id, timedelta(minutes=15))
    return session_id

# Route to generate the token
async def generate_token_route(request):
    data = await request.json()
    user_id = data.get('user_id')
    permissions = data.get('permissions')

    if not user_id or not permissions:
        return JSONResponse({"error": "Invalid request"}, status_code=400)

    # Generate the JWT token
    token = generate_jwt_token(user_id, permissions)

    # Optionally, store session in Redis
    set_session(token)

    return JSONResponse({"token": token})

# Starlette app setup
app = Starlette(debug=True)
app.add_route("/generate-token", generate_token_route, methods=["POST"])

# Main entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
