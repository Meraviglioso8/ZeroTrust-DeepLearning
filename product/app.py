# product_service.py

import os
from typing import List, Optional
from dotenv import load_dotenv

import strawberry
from strawberry.asgi import GraphQL
from strawberry.types import Info

from starlette.applications import Starlette
from starlette.responses import HTMLResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, ForeignKey
)
from sqlalchemy.orm import (
    sessionmaker, relationship, declarative_base,
    scoped_session, joinedload
)

# ─── ENVIRONMENT SETUP ─────────────────────────────────────────────────────
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")  # e.g. "postgresql://user:pass@host/db"

# ─── DATABASE SETUP ───────────────────────────────────────────────────────
engine = create_engine(DATABASE_URL, future=True)
SessionLocal = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
)
Base = declarative_base()

class Product(Base):
    __tablename__ = "products"
    id          = Column(Integer, primary_key=True)
    name        = Column(String(100))
    description = Column(String(200))
    price       = Column(Float)
    comments    = relationship("Comment", back_populates="product", cascade="all, delete-orphan")
    ratings     = relationship("Rating",  back_populates="product", cascade="all, delete-orphan")

class Comment(Base):
    __tablename__ = "comments"
    id         = Column(Integer, primary_key=True)
    text       = Column(String(300))
    product_id = Column(Integer, ForeignKey("products.id"))
    product    = relationship("Product", back_populates="comments")

class Rating(Base):
    __tablename__ = "ratings"
    id         = Column(Integer, primary_key=True)
    score      = Column(Float)
    product_id = Column(Integer, ForeignKey("products.id"))
    product    = relationship("Product", back_populates="ratings")

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# ─── GRAPHQL SCHEMA ───────────────────────────────────────────────────────
@strawberry.type
class ProductType:
    id: int
    name: str
    description: str
    price: float

@strawberry.type
class Query:
    @strawberry.field
    def all_products(self, info: Info) -> List[ProductType]:
        db = SessionLocal()
        products = db.query(Product).options(
            joinedload(Product.comments),
            joinedload(Product.ratings)
        ).all()
        db.close()
        return [
            ProductType(
                id=p.id,
                name=p.name,
                description=p.description,
                price=p.price
            )
            for p in products
        ]

    @strawberry.field
    def product(self, info: Info, id: int) -> Optional[ProductType]:
        db = SessionLocal()
        p = db.query(Product).get(id)
        db.close()
        if not p:
            return None
        return ProductType(
            id=p.id,
            name=p.name,
            description=p.description,
            price=p.price
        )

schema = strawberry.Schema(query=Query)
graphql_app = GraphQL(
    schema,
    graphql_ide=True,
    allow_queries_via_get=True,
)

# ─── STARLETTE APP & ROUTES ─────────────────────────────────────────────
app = Starlette(debug=True)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Mount GraphQL at /graphql
app.add_route("/graphql", graphql_app)
app.add_websocket_route("/graphql", graphql_app)

# HTML Products page
@app.route("/products")
async def products(request: Request):
    order_id = request.query_params.get("order_id")
    payment  = request.query_params.get("payment")

    # Load all products from DB
    db = SessionLocal()
    prods = db.query(Product).all()
    db.close()

    items = [
        {"id": p.id, "name": p.name, "description": p.description, "price": p.price}
        for p in prods
    ]

    banner = ""
    if order_id and payment == "success":
        banner = f"<p style='color:green;'>Payment for order #{order_id} succeeded.</p>"
    elif order_id and payment == "cancel":
        banner = f"<p style='color:red;'>Payment for order #{order_id} cancelled.</p>"

    rows = "".join(
        f"<tr>"
        f"<td>{i['id']}</td>"
        f"<td>{i['name']}</td>"
        f"<td>{i['description']}</td>"
        f"<td>{i['price']}</td>"
        f"<td>"
        f"<a href='http://localhost:8000/payments/create/{i['id']}' "
        f"   style='padding:6px 12px;background:#28a745;color:#fff;"
        f"text-decoration:none;border-radius:4px;'>Buy</a>"
        f"</td>"
        f"</tr>"
        for i in items
    )

    html = f"""
    <!DOCTYPE html>
    <html lang='en'>
    <head><meta charset='utf-8'><title>Products</title></head>
    <body>
      <h1>All Products</h1>
      {banner}
      <table border='1' cellpadding='6' cellspacing='0'>
        <thead>
          <tr>
            <th>ID</th><th>Name</th><th>Description</th><th>Price</th><th>Action</th>
          </tr>
        </thead>
        <tbody>
          {rows}
        </tbody>
      </table>
    </body>
    </html>
    """
    return HTMLResponse(html)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5002)
