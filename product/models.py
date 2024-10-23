# from flask_sqlalchemy import SQLAlchemy

# db = SQLAlchemy()

# class Product(db.Model):
#     __tablename__ = 'products'
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100))
#     description = db.Column(db.String(200))
#     price = db.Column(db.Float)
#     comments = db.relationship('Comment', backref='product', lazy=True)
#     ratings = db.relationship('Rating', backref='product', lazy=True)

# class Comment(db.Model):
#     __tablename__ = 'comments'
#     id = db.Column(db.Integer, primary_key=True)
#     text = db.Column(db.String(300))
#     product_id = db.Column(db.Integer, db.ForeignKey('products.id'))

# class Rating(db.Model):
#     __tablename__ = 'ratings'
#     id = db.Column(db.Integer, primary_key=True)
#     score = db.Column(db.Float)
#     product_id = db.Column(db.Integer, db.ForeignKey('products.id'))

# class Order(db.Model):
#     __tablename__ = 'orders'
#     id = db.Column(db.Integer, primary_key=True)
#     product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
#     quantity = db.Column(db.Integer)
#     total_price = db.Column(db.Float)
