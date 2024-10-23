# import strawberry
# from typing import List, Optional
# from models import Product, Comment, Rating, Order
# from app import db
# from flask import current_app
# from functools import wraps

# def with_app_context(func):
#     @wraps(func)
#     def wrapper(*args, **kwargs):
#         with current_app.app_context():
#             return func(*args, **kwargs)
#     return wrapper

# @strawberry.type
# class CommentType:
#     id: int
#     text: str
#     product_id: int

# @strawberry.type
# class RatingType:
#     id: int
#     score: float
#     product_id: int

# @strawberry.type
# class OrderType:
#     id: int
#     quantity: int
#     total_price: float
#     product_id: int

# @strawberry.type
# class ProductType:
#     id: int
#     name: str
#     description: str
#     price: float
#     comments: List[CommentType]
#     ratings: List[RatingType]

# @strawberry.type
# class Query:
#     @strawberry.field
#     def all_products(self) -> List[ProductType]:
#         with current_app.app_context():
#             products = Product.query.all()
#             return [
#                 ProductType(
#                     id=product.id,
#                     name=product.name,
#                     description=product.description,
#                     price=product.price,
#                     comments=[CommentType(id=comment.id, text=comment.text, product_id=comment.product_id) for comment in product.comments],
#                     ratings=[RatingType(id=rating.id, score=rating.score, product_id=rating.product_id) for rating in product.ratings]
#                 ) for product in products
#             ]

#     @strawberry.field
#     def all_comments(self) -> List[CommentType]:
#         comments = Comment.query.all()
#         return [CommentType(id=comment.id, text=comment.text, product_id=comment.product_id) for comment in comments]

#     @strawberry.field
#     def all_ratings(self) -> List[RatingType]:
#         ratings = Rating.query.all()
#         return [RatingType(id=rating.id, score=rating.score, product_id=rating.product_id) for rating in ratings]

#     @strawberry.field
#     def all_orders(self) -> List[OrderType]:
#         orders = Order.query.all()
#         return [OrderType(id=order.id, quantity=order.quantity, total_price=order.total_price, product_id=order.product_id) for order in orders]

#     @strawberry.field
#     def product(self, id: int) -> Optional[ProductType]:
#         product = Product.query.get(id)
#         if product:
#             return ProductType(
#                 id=product.id,
#                 name=product.name,
#                 description=product.description,
#                 price=product.price,
#                 comments=[CommentType(id=comment.id, text=comment.text, product_id=comment.product_id) for comment in product.comments],
#                 ratings=[RatingType(id=rating.id, score=rating.score, product_id=rating.product_id) for rating in product.ratings]
#             )
#         return None

# @strawberry.type
# class Mutation:
#     @strawberry.mutation
#     @with_app_context
#     def add_product(self, name: str, description: str, price: float) -> ProductType:
#         new_product = Product(name=name, description=description, price=price)
#         db.session.add(new_product)
#         db.session.commit()
#         return ProductType(
#             id=new_product.id,
#             name=new_product.name,
#             description=new_product.description,
#             price=new_product.price,
#             comments=[],
#             ratings=[]
#         )

#     @strawberry.mutation
#     @with_app_context
#     def remove_product(self, id: int) -> bool:
#         product = Product.query.get(id)
#         if product:
#             db.session.delete(product)
#             db.session.commit()
#             return True
#         return False

#     @strawberry.mutation
#     @with_app_context
#     def add_comment(self, product_id: int, text: str) -> CommentType:
#         new_comment = Comment(product_id=product_id, text=text)
#         db.session.add(new_comment)
#         db.session.commit()
#         return CommentType(id=new_comment.id, text=new_comment.text, product_id=new_comment.product_id)

#     @strawberry.mutation
#     @with_app_context
#     def add_rating(self, product_id: int, score: float) -> RatingType:
#         new_rating = Rating(product_id=product_id, score=score)
#         db.session.add(new_rating)
#         db.session.commit()
#         return RatingType(id=new_rating.id, score=new_rating.score, product_id=new_rating.product_id)

#     @strawberry.mutation
#     @with_app_context
#     def add_order(self, product_id: int, quantity: int, total_price: float) -> OrderType:
#         new_order = Order(product_id=product_id, quantity=quantity, total_price=total_price)
#         db.session.add(new_order)
#         db.session.commit()
#         return OrderType(id=new_order.id, quantity=new_order.quantity, total_price=new_order.total_price, product_id=new_order.product_id)

# schema = strawberry.Schema(query=Query, mutation=Mutation)
