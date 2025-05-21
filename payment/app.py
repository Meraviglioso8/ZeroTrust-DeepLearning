# payment_service.py
import os
from typing import Optional, Dict
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import RedirectResponse, JSONResponse
from starlette.middleware.cors import CORSMiddleware
from keycloak import KeycloakOpenID
import requests
import paypalrestsdk
from sqlalchemy import create_engine, Column, Integer, Float, String
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

KEYCLOAK_SERVER   = os.getenv("KEYCLOAK_SERVER")
REALM             = os.getenv("KEYCLOAK_REALM")
CLIENT_ID         = os.getenv("KEYCLOAK_CLIENT_ID")
CLIENT_SECRET     = os.getenv("KEYCLOAK_CLIENT_SECRET")
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL")  # e.g. http://localhost:5002
APP_HOST          = os.getenv("APP_HOST", "http://localhost:8000")
DATABASE_URL      = os.getenv("DATABASE_URL")

kc = KeycloakOpenID(
    server_url    = KEYCLOAK_SERVER,
    realm_name    = REALM,
    client_id     = CLIENT_ID,
    client_secret_key = CLIENT_SECRET,
    verify        = True,
)

paypalrestsdk.configure({
    "mode":          os.getenv("PAYPAL_MODE"),
    "client_id":     os.getenv("PAYPAL_CLIENT_ID"),
    "client_secret": os.getenv("PAYPAL_CLIENT_SECRET"),
})

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Payment(Base):
    __tablename__ = "payments"
    id       = Column(Integer, primary_key=True)
    order_id = Column(Integer, nullable=False)
    amount   = Column(Float,   nullable=False)
    status   = Column(String(50), nullable=False)

Base.metadata.create_all(engine)


def introspect_token(token: str) -> Optional[Dict]:
    info = kc.introspect(token)
    return info if info.get("active") else None


def fetch_order(order_id: int, token: str) -> Dict:
    # Query the 'product' field, not 'order'
    query = """
      query GetProduct($id:Int!) {
        product(id:$id) {
          id
          price
        }
      }
    """
    resp = requests.post(
        PRODUCT_SERVICE_URL.rstrip("/") + "/graphql",
        json={"query": query, "variables": {"id": order_id}},
        headers={"Authorization": f"Bearer {token}"},
        timeout=5,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("errors"):
        raise Exception(data["errors"])
    # Now your data lives under data["data"]["product"]
    return data["data"]["product"]


def create_paypal_payment(total: float, order_id: int):
    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer":  {"payment_method": "paypal"},
        "transactions": [{
            "amount": {"total": f"{total:.2f}", "currency": "USD"},
            "description": f"Order #{order_id}"
        }],
        "redirect_urls": {
            "return_url": f"{APP_HOST}/payments/execute?order_id={order_id}",
            "cancel_url": f"{APP_HOST}/payments/cancel?order_id={order_id}"
        }
    })
    if not payment.create():
        raise Exception(payment.error)
    return payment


app = Starlette(debug=True)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.route("/payments/create/{order_id:int}")
async def create_payment(request: Request) -> RedirectResponse:
    # read token from Authorization header or cookie
    auth_h = request.headers.get("Authorization", "")
    if auth_h.startswith("Bearer "):
        token = auth_h.split(None, 1)[1]
    else:
        token = request.cookies.get("access_token")

    if not token:
        return JSONResponse({"detail": "Missing token"}, status_code=401)

    user = introspect_token(token)
    if not user:
        return JSONResponse({"detail": "Invalid token"}, status_code=401)

    order = fetch_order(request.path_params["order_id"], token)
    if not order:
        return JSONResponse({"detail": "Order not found"}, status_code=404)

    # here order["price"] is your amount
    payment = create_paypal_payment(order["price"], order["id"])

    db = SessionLocal()
    db.add(Payment(order_id=order["id"], amount=order["price"], status="Pending"))
    db.commit()
    db.close()

    # redirect user to PayPal approval
    link = next(l for l in payment.links if l.rel == "approval_url")
    return RedirectResponse(link.href)


@app.route("/payments/execute")
async def execute_payment(request: Request) -> RedirectResponse:
    payer_id   = request.query_params.get("PayerID")
    payment_id = request.query_params.get("paymentId")
    order_id   = request.query_params.get("order_id")

    payment = paypalrestsdk.Payment.find(payment_id)
    if not payment.execute({"payer_id": payer_id}):
        return JSONResponse({"detail": "Execution failed"}, status_code=400)

    db = SessionLocal()
    pay = (
        db.query(Payment)
        .filter(Payment.order_id == int(order_id))
        .order_by(Payment.id.desc())
        .first()
    )
    pay.status = "Completed"
    db.commit()
    db.close()

    return RedirectResponse(f"{PRODUCT_SERVICE_URL}/products?order_id={order_id}&payment=success")


@app.route("/payments/cancel")
async def cancel_payment(request: Request) -> RedirectResponse:
    order_id = request.query_params.get("order_id")
    return RedirectResponse(f"{PRODUCT_SERVICE_URL}/products?order_id={order_id}&payment=cancel")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
