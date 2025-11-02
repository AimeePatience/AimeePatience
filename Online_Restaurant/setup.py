#!/usr/bin/env python
"""
Setup script to initialize the database with sample data.
Run this after first installation to populate the database with test data.
"""

from app import app
from models import db, User, Menu
from werkzeug.security import generate_password_hash

def init_db():
    """Initialize database with sample data"""
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created.")
        
        # Create manager if doesn't exist
        if not User.query.filter_by(username='manager').first():
            manager = User(
                username='manager',
                email='manager@restaurant.com',
                role='Manager'
            )
            manager.set_password('manager123')
            db.session.add(manager)
            print("Default manager account created (username: manager, password: manager123)")
        
        # Create sample chef
        if not User.query.filter_by(username='chef1').first():
            chef = User(
                username='chef1',
                email='chef1@restaurant.com',
                role='Chef',
                is_active=True,
                salary=50000.0
            )
            chef.set_password('chef123')
            db.session.add(chef)
            print("Sample chef created (username: chef1, password: chef123)")
        
        # Create sample delivery person
        if not User.query.filter_by(username='delivery1').first():
            delivery = User(
                username='delivery1',
                email='delivery1@restaurant.com',
                role='DeliveryPerson',
                is_active=True,
                salary=30000.0
            )
            delivery.set_password('delivery123')
            db.session.add(delivery)
            print("Sample delivery person created (username: delivery1, password: delivery123)")
        
        # Create sample menu items if none exist
        if Menu.query.count() == 0:
            chef = User.query.filter_by(role='Chef').first()
            chef_id = chef.id if chef else None
            
            menu_items = [
                Menu(
                    name='Margherita Pizza',
                    description='Classic pizza with tomato, mozzarella, and basil',
                    price=12.99,
                    category='Pizza',
                    chef_id=chef_id,
                    is_available=True
                ),
                Menu(
                    name='Caesar Salad',
                    description='Fresh romaine lettuce with caesar dressing and croutons',
                    price=8.99,
                    category='Salad',
                    chef_id=chef_id,
                    is_available=True
                ),
                Menu(
                    name='Grilled Chicken',
                    description='Tender grilled chicken breast with vegetables',
                    price=15.99,
                    category='Main Course',
                    chef_id=chef_id,
                    is_available=True
                ),
                Menu(
                    name='Chocolate Cake',
                    description='Rich chocolate cake with frosting',
                    price=6.99,
                    category='Dessert',
                    chef_id=chef_id,
                    is_available=True
                ),
                Menu(
                    name='Burger Deluxe',
                    description='Beef patty with lettuce, tomato, cheese, and special sauce',
                    price=10.99,
                    category='Main Course',
                    chef_id=chef_id,
                    is_available=True
                )
            ]
            
            for item in menu_items:
                db.session.add(item)
            print(f"Added {len(menu_items)} sample menu items.")
        
        db.session.commit()
        print("\nSetup complete!")
        print("\nDefault accounts:")
        print("  Manager: username=manager, password=manager123")
        print("  Chef: username=chef1, password=chef123")
        print("  Delivery: username=delivery1, password=delivery123")
        print("\nNote: Change passwords in production!")

if __name__ == '__main__':
    init_db()

