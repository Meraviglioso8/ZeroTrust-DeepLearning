from flask import Flask, current_app
from flask_sqlalchemy import SQLAlchemy
from strawberry.flask.views import GraphQLView
import strawberry
from config import Config
from typing import List, Optional
from flask_migrate import Migrate

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.String(200))
    price = db.Column(db.Float)
    comments = db.relationship('Comment', backref='product', lazy=True)
    ratings = db.relationship('Rating', backref='product', lazy=True)

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(300))
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))

class Rating(db.Model):
    __tablename__ = 'ratings'
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Float)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    quantity = db.Column(db.Integer)
    total_price = db.Column(db.Float)

@strawberry.type
class CommentType:
    id: int
    text: str
    product_id: int

@strawberry.type
class RatingType:
    id: int
    score: float
    product_id: int

@strawberry.type
class OrderType:
    id: int
    quantity: int
    total_price: float
    product_id: int

@strawberry.type
class ProductType:
    id: int
    name: str
    description: str
    price: float
    comments: List[CommentType]
    ratings: List[RatingType]

@strawberry.type
class Query:
    @strawberry.field
    def all_products(self) -> List[ProductType]:
        with app.app_context():
            products = Product.query.all()
            return [
                ProductType(
                    id=product.id,
                    name=product.name,
                    description=product.description,
                    price=product.price,
                    comments=[CommentType(id=comment.id, text=comment.text, product_id=comment.product_id) for comment in product.comments],
                    ratings=[RatingType(id=rating.id, score=rating.score, product_id=rating.product_id) for rating in product.ratings]
                ) for product in products
            ]

    @strawberry.field
    def order(self, id: int) -> Optional[OrderType]:
        with app.app_context():
            order = Order.query.get(id)
            if order:
                return OrderType(
                    id=order.id,
                    quantity=order.quantity,
                    total_price=order.total_price,
                    product_id=order.product_id
                )
            return None
    
    @strawberry.field
    def product(self, id: int) -> Optional[ProductType]:
        with app.app_context():
            product = Product.query.get(id)
            if product:
                return ProductType(
                    id=product.id,
                    name=product.name,
                    description=product.description,
                    price=product.price,
                    comments=[CommentType(id=comment.id, text=comment.text, product_id=comment.product_id) for comment in product.comments],
                    ratings=[RatingType(id=rating.id, score=rating.score, product_id=rating.product_id) for rating in product.ratings]
                )
            return None

@strawberry.type
class Mutation:
    @strawberry.mutation
    def add_product(self, name: str, description: str, price: float) -> ProductType:
        with app.app_context():
            new_product = Product(name=name, description=description, price=price)
            db.session.add(new_product)
            db.session.commit()
            return ProductType(
                id=new_product.id,
                name=new_product.name,
                description=new_product.description,
                price=new_product.price,
                comments=[],
                ratings=[]
            )

    @strawberry.mutation
    def remove_product(self, id: int) -> bool:
        with app.app_context():
            product = Product.query.get(id)
            if product:
                db.session.delete(product)
                db.session.commit()
                return True
            return False

    @strawberry.mutation
    def add_comment(self, product_id: int, text: str) -> CommentType:
        with app.app_context():
            new_comment = Comment(product_id=product_id, text=text)
            db.session.add(new_comment)
            db.session.commit()
            return CommentType(id=new_comment.id, text=new_comment.text, product_id=new_comment.product_id)

    @strawberry.mutation
    def add_rating(self, product_id: int, score: float) -> RatingType:
        with app.app_context():
            new_rating = Rating(product_id=product_id, score=score)
            db.session.add(new_rating)
            db.session.commit()
            return RatingType(id=new_rating.id, score=new_rating.score, product_id=new_rating.product_id)

    @strawberry.mutation
    def add_order(self, product_id: int, quantity: int, total_price: float) -> OrderType:
        with app.app_context():
            new_order = Order(product_id=product_id, quantity=quantity, total_price=total_price)
            db.session.add(new_order)
            db.session.commit()
            return OrderType(id=new_order.id, quantity=new_order.quantity, total_price=new_order.total_price, product_id=new_order.product_id)

schema = strawberry.Schema(query=Query, mutation=Mutation)

# app context fucking shiet
with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        print(f"Error creating tables: {e}")

app.add_url_rule(
    '/graphql',
    view_func=GraphQLView.as_view('graphql_view', schema=schema)
)

if __name__ == '__main__':
    app.run(debug=True)
