#!/usr/bin/env python3
import os
from dotenv import load_dotenv

# 1) load .env so DATABASE_URL, etc. are available
load_dotenv()

# 2) import your SQLAlchemy setup and models
from app import SessionLocal, Base, engine
from app import Product, Comment, Rating, Order

def main():
    # 3) (re)create tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # 4) create some products
    p1 = Product(
        name="Wireless Mouse",
        description="Ergonomic wireless mouse with USB-C charging",
        price=29.99
    )
    p2 = Product(
        name="Mechanical Keyboard",
        description="75% layout, hot-swappable switches",
        price=89.50
    )
    db.add_all([p1, p2])
    db.commit()  # so p1.id and p2.id are populated

    # 5) add comments & ratings to p1
    c1 = Comment(text="Really comfortable!", product_id=p1.id)
    c2 = Comment(text="Battery lasts forever", product_id=p1.id)
    r1 = Rating(score=4.5, product_id=p1.id)
    r2 = Rating(score=5.0, product_id=p1.id)
    db.add_all([c1, c2, r1, r2])
    db.commit()

    # 6) add an order for p2
    order = Order(
        product_id=p2.id,
        quantity=3,
        total_price=p2.price * 3
    )
    db.add(order)
    db.commit()

    print(f"Inserted Products: {p1.id}, {p2.id}")
    print(f"Inserted Comments: {c1.id}, {c2.id}")
    print(f"Inserted Ratings: {r1.id}, {r2.id}")
    print(f"Inserted Order: {order.id}")

    db.close()

if __name__ == "__main__":
    main()
