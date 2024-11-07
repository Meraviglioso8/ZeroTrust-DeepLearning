from flask import Flask, jsonify, request, g
from flask_sqlalchemy import SQLAlchemy
import paypalrestsdk
from strawberry.flask.views import GraphQLView
import strawberry
import jwt
import requests
from config import Config
from typing import List, Optional

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)


@app.before_request
def before_request():
    try:
        if request.method != 'OPTIONS':
            print("Before request called")
            print("Request Headers:", request.headers)
            token = request.headers.get('Authorization')
            print("Authorization Header:", token)
            if token:
                token = token.split(" ")[1]
                print("Token found:", token)  
                try:
                    payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
                    print("Decoded payload:", payload)
                    g.user = payload
                except jwt.ExpiredSignatureError:
                    return jsonify({"error": "Token expired"}), 401
                except jwt.InvalidTokenError:
                    return jsonify({"error": "Invalid token"}), 401
            else:
                print("No token found")
                g.user = None
    except Exception as e:
        return "401 Unauthorized\n{}\n\n".format(e), 401

       
def require_permissions(allowed_permissions):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = g.get('user') 
            print("User in require_permissions:", user)  
            if not user or not set(user.get('permissions', [])).intersection(allowed_permissions):
                print("Unauthorized access")  
                raise Exception("Unauthorized access")
            return fn(*args, **kwargs)
        return wrapper
    return decorator

paypalrestsdk.configure({
    "mode": app.config["PAYPAL_MODE"],
    "client_id": app.config["PAYPAL_CLIENT_ID"],
    "client_secret": app.config["PAYPAL_CLIENT_SECRET"]
})


class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer)
    amount = db.Column(db.Float)
    status = db.Column(db.String(50))

def fetch_order(order_id: int):
    query = """
    query GetOrder($id: Int!) {
        order(id: $id) {
            id
            totalPrice
        }
    }
    """
    variables = {"id": order_id}
    response = requests.post(
        app.config["PRODUCT_SERVICE_URL"], 
        json={"query": query, "variables": variables}
    )
    data = response.json()
    if "errors" in data:
        raise Exception(data["errors"])
    return data["data"]["order"]

def process_paypal_payment(order_total: float) -> dict:
    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {
            "payment_method": "paypal"},
        "transactions": [{
            "amount": {
                "total": f"{order_total:.2f}",
                "currency": "USD"},
            "description": "pay"}],
        "redirect_urls": {
            "return_url": "uit.edu.vn",  
            "cancel_url": "courses.uit.edu.vn"}
    })

    if payment.create():
        print("Payment created")
        return {"paymentID": payment.id, "links": payment.links}
    else:
        print(payment.error)
        raise Exception("Error creating payment")

@strawberry.type
class Query:
    with app.app_context():
        hello: str = "Hello, this is a placeholder query."

@strawberry.type
class Mutation:
    @strawberry.mutation
    def process_payment(self, order_id: int) -> str:
        with app.app_context():
            order = fetch_order(order_id)
            if not order:
                raise Exception("Order not found")
            total_price = order["totalPrice"]
            print("Total price is" + str(total_price))
            payment_response = process_paypal_payment(total_price)

            new_payment = Payment(order_id=order_id, amount=total_price, status="Pending")
            db.session.add(new_payment)
            db.session.commit()

            for link in payment_response['links']:
                if link['rel'] == 'approval_url':
                    return link['href']

            return "Error: PayPal approval URL not found"
        
class CustomGraphQLView(GraphQLView):
    def get_context(self, request, response=None) -> dict:
        context = super().get_context(request, response)
        context['token'] = g.get('user') 
        return context


schema = strawberry.Schema(query=Query, mutation=Mutation)

app.add_url_rule(
    '/graphql',
    view_func=CustomGraphQLView.as_view('graphql_view', schema=schema)
)


with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
