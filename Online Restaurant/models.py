from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Visitor')  # Visitor, Customer, VIP, Chef, DeliveryPerson, Manager
    balance = db.Column(db.Float, default=0.0)
    salary = db.Column(db.Float, default=0.0)  # For employees
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    orders_placed = db.relationship('Order', foreign_keys='Order.customer_id', backref='customer', lazy='dynamic')
    orders_delivered = db.relationship('Order', foreign_keys='Order.delivery_person_id', backref='delivery_person', lazy='dynamic')
    complaints_filed = db.relationship('Complaint', foreign_keys='Complaint.filed_by_id', backref='filer', lazy='dynamic')
    complaints_received = db.relationship('Complaint', foreign_keys='Complaint.filed_against_id', backref='target', lazy='dynamic')
    compliments_filed = db.relationship('Compliment', foreign_keys='Compliment.filed_by_id', backref='filer', lazy='dynamic')
    compliments_received = db.relationship('Compliment', foreign_keys='Compliment.filed_against_id', backref='target', lazy='dynamic')
    warnings = db.relationship('Warning', backref='user', lazy='dynamic')
    ratings_given = db.relationship('Rating', foreign_keys='Rating.customer_id', lazy='dynamic')
    menu_items = db.relationship('Menu', backref='chef', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_vip(self):
        return self.role == 'VIP'
    
    def is_chef(self):
        return self.role == 'Chef'
    
    def is_delivery(self):
        return self.role == 'DeliveryPerson'
    
    def is_manager(self):
        return self.role == 'Manager'
    
    def is_customer(self):
        return self.role in ['Customer', 'VIP']

class Menu(db.Model):
    __tablename__ = 'menu'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    image_path = db.Column(db.String(255))
    chef_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    category = db.Column(db.String(50))
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    order_items = db.relationship('OrderItem', backref='menu_item', lazy='dynamic')
    ratings = db.relationship('Rating', backref='menu_item', lazy='dynamic')
    
    def average_rating(self):
        ratings = self.ratings.all()
        if not ratings:
            return 0.0
        return sum(r.rating for r in ratings) / len(ratings)

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    delivery_person_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    status = db.Column(db.String(20), default='Pending')  # Pending, Preparing, Ready, Out for Delivery, Delivered, Cancelled
    total_amount = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    delivery_address = db.Column(db.Text)
    notes = db.Column(db.Text)
    
    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy='dynamic', cascade='all, delete-orphan')
    complaints = db.relationship('Complaint', backref='order', lazy='dynamic')
    compliments = db.relationship('Compliment', backref='order', lazy='dynamic')
    ratings = db.relationship('Rating', backref='order', lazy='dynamic')
    bids = db.relationship('DeliveryBid', backref='order', lazy='dynamic', cascade='all, delete-orphan')

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    subtotal = db.Column(db.Float, nullable=False)

class Complaint(db.Model):
    __tablename__ = 'complaints'
    
    id = db.Column(db.Integer, primary_key=True)
    filed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filed_against_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    type = db.Column(db.String(50))  # e.g., 'quality', 'service', 'delivery', 'behavior'
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Pending')  # Pending, Approved, Rejected
    manager_decision = db.Column(db.String(20))  # Approved, Rejected
    manager_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)

class Compliment(db.Model):
    __tablename__ = 'compliments'
    
    id = db.Column(db.Integer, primary_key=True)
    filed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filed_against_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    type = db.Column(db.String(50))
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Pending')
    manager_decision = db.Column(db.String(20))
    manager_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)

class Rating(db.Model):
    __tablename__ = 'ratings'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    chef_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu.id'), nullable=True)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships with explicit foreign keys
    chef = db.relationship('User', foreign_keys=[chef_id], backref='ratings_received')

class Warning(db.Model):
    __tablename__ = 'warnings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Blacklist(db.Model):
    __tablename__ = 'blacklist'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    reason = db.Column(db.Text, nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('blacklist_entry', uselist=False))

class DeliveryBid(db.Model):
    __tablename__ = 'delivery_bids'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    delivery_person_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    bid_amount = db.Column(db.Float)
    status = db.Column(db.String(20), default='Pending')  # Pending, Accepted, Rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    delivery_person = db.relationship('User', backref='bids')

class KnowledgeBaseEntry(db.Model):
    __tablename__ = 'knowledge_base_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Float, default=0.0)  # Average rating
    rating_count = db.Column(db.Integer, default=0)
    flagged = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    ratings_list = db.relationship('AIResponseRating', backref='kb_entry', lazy='dynamic')

class AIResponseRating(db.Model):
    __tablename__ = 'ai_response_ratings'
    
    id = db.Column(db.Integer, primary_key=True)
    kb_entry_id = db.Column(db.Integer, db.ForeignKey('knowledge_base_entries.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    query = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 0-5 stars
    source = db.Column(db.String(20))  # 'local' or 'llm'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


