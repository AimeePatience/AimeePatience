from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Menu, Order, OrderItem, Complaint, Compliment, Rating, Warning, Blacklist, DeliveryBid, KnowledgeBaseEntry, AIResponseRating
from config import Config
from utils import calculate_vip_status, process_complaint_decision, get_user_total_spending, can_user_place_order
from ai_service import get_ai_service
from functools import wraps
from datetime import datetime
import os

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Role-based access control decorators
def role_required(*roles):
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if current_user.role not in roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Initialize database
with app.app_context():
    db.create_all()
    
    # Create default manager account if it doesn't exist
    if not User.query.filter_by(username='manager').first():
        manager = User(
            username='manager',
            email='manager@restaurant.com',
            role='Manager'
        )
        manager.set_password('manager123')
        db.session.add(manager)
        db.session.commit()

# Routes
@app.route('/')
def index():
    """Home page with menu browsing"""
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    
    query = Menu.query.filter_by(is_available=True)
    
    if search:
        query = query.filter(Menu.name.contains(search) | Menu.description.contains(search))
    if category:
        query = query.filter_by(category=category)
    
    menu_items = query.all()
    
    # Personalized menu for logged-in users
    personalized_items = {}
    if current_user.is_authenticated and current_user.is_customer():
        from sqlalchemy import func
        # Most ordered items
        most_ordered = db.session.query(
            OrderItem.menu_item_id,
            func.sum(OrderItem.quantity).label('total_quantity')
        ).join(Order).filter(
            Order.customer_id == current_user.id,
            Order.status == 'Delivered'
        ).group_by(OrderItem.menu_item_id).order_by(func.sum(OrderItem.quantity).desc()).limit(5).all()
        
        # Highest rated items
        highest_rated = Menu.query.join(Rating).filter(
            Rating.customer_id == current_user.id
        ).order_by(Rating.rating.desc()).limit(5).all()
        
        personalized_items = {
            'most_ordered': [db.session.get(Menu, item_id) for item_id, _ in most_ordered if item_id],
            'highest_rated': highest_rated
        }
    
    categories = db.session.query(Menu.category).distinct().all()
    categories = [c[0] for c in categories if c[0]]
    
    return render_template('index.html', 
                         menu_items=menu_items, 
                         search=search,
                         category=category,
                         categories=categories,
                         personalized_items=personalized_items)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'Customer')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please wait for manager approval.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_active:
            login_user(user)
            next_page = request.args.get('next') or url_for('index')
            return redirect(next_page)
        else:
            flash('Invalid username or password, or account is inactive.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    session.pop('cart', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/add_to_cart/<int:menu_id>', methods=['POST'])
def add_to_cart(menu_id):
    """Add item to shopping cart"""
    if 'cart' not in session:
        session['cart'] = {}
    
    menu_item = db.session.get(Menu, menu_id)
    if not menu_item:
        flash('Menu item not found.', 'danger')
        return redirect(url_for('index'))
    quantity = int(request.form.get('quantity', 1))
    
    cart = session['cart']
    if str(menu_id) in cart:
        cart[str(menu_id)]['quantity'] += quantity
    else:
        cart[str(menu_id)] = {
            'name': menu_item.name,
            'price': float(menu_item.price),
            'quantity': quantity,
            'image': menu_item.image_path or 'default.jpg'
        }
    
    session['cart'] = cart
    flash(f'{menu_item.name} added to cart.', 'success')
    return redirect(url_for('index'))

@app.route('/cart')
@login_required
def view_cart():
    """View shopping cart"""
    cart = session.get('cart', {})
    total = sum(item['price'] * item['quantity'] for item in cart.values())
    return render_template('cart.html', cart=cart, total=total)

@app.route('/remove_from_cart/<int:menu_id>', methods=['POST'])
@login_required
def remove_from_cart(menu_id):
    """Remove item from cart"""
    cart = session.get('cart', {})
    cart.pop(str(menu_id), None)
    session['cart'] = cart
    flash('Item removed from cart.', 'info')
    return redirect(url_for('view_cart'))

@app.route('/place_order', methods=['POST'])
@login_required
@role_required('Customer', 'VIP')
def place_order():
    """Place an order"""
    can_order, error_msg = can_user_place_order(current_user.id)
    if not can_order:
        flash(error_msg, 'danger')
        return redirect(url_for('view_cart'))
    
    cart = session.get('cart', {})
    if not cart:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('view_cart'))
    
    # Calculate total
    total = sum(item['price'] * item['quantity'] for item in cart.values())
    
    # Check balance
    if current_user.balance < total:
        flash('Insufficient balance. Please deposit money first.', 'danger')
        return redirect(url_for('view_cart'))
    
    # Create order
    order = Order(
        customer_id=current_user.id,
        total_amount=total,
        delivery_address=request.form.get('delivery_address', ''),
        notes=request.form.get('notes', ''),
        status='Pending'
    )
    db.session.add(order)
    db.session.flush()
    
    # Create order items
    for menu_id, item_data in cart.items():
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=int(menu_id),
            quantity=item_data['quantity'],
            subtotal=item_data['price'] * item_data['quantity']
        )
        db.session.add(order_item)
    
    # Deduct balance
    current_user.balance -= total
    db.session.commit()
    
    # Clear cart
    session['cart'] = {}
    
    # Check VIP status
    calculate_vip_status(current_user.id)
    
    flash(f'Order #{order.id} placed successfully!', 'success')
    return redirect(url_for('order_history'))

@app.route('/order_history')
@login_required
@role_required('Customer', 'VIP')
def order_history():
    """View order history"""
    orders = Order.query.filter_by(customer_id=current_user.id).order_by(Order.timestamp.desc()).all()
    return render_template('order_history.html', orders=orders)

@app.route('/deposit', methods=['GET', 'POST'])
@login_required
@role_required('Customer', 'VIP')
def deposit():
    """Deposit money to account"""
    if request.method == 'POST':
        amount = float(request.form.get('amount', 0))
        if amount > 0:
            current_user.balance += amount
            db.session.commit()
            flash(f'${amount:.2f} deposited successfully. New balance: ${current_user.balance:.2f}', 'success')
            return redirect(url_for('deposit'))
        else:
            flash('Invalid amount.', 'danger')
    
    return render_template('deposit.html')

@app.route('/rate_chef/<int:order_id>', methods=['GET', 'POST'])
@login_required
@role_required('Customer', 'VIP')
def rate_chef(order_id):
    """Rate chef after order delivery"""
    order = db.session.get(Order, order_id)
    if not order:
        flash('Order not found.', 'danger')
        return redirect(url_for('order_history'))
    
    if order.customer_id != current_user.id:
        flash('You can only rate orders you placed.', 'danger')
        return redirect(url_for('order_history'))
    
    if order.status != 'Delivered':
        flash('You can only rate delivered orders.', 'warning')
        return redirect(url_for('order_history'))
    
    if request.method == 'POST':
        rating_value = int(request.form.get('rating', 0))
        comment = request.form.get('comment', '')
        menu_item_id = request.form.get('menu_item_id')
        
        # Find chef from order items
        order_item = order.items.first()
        if order_item:
            menu_item = db.session.get(Menu, order_item.menu_item_id)
            chef_id = menu_item.chef_id if menu_item else None
            
            if chef_id:
                rating = Rating(
                    order_id=order.id,
                    chef_id=chef_id,
                    customer_id=current_user.id,
                    menu_item_id=menu_item_id if menu_item_id else None,
                    rating=rating_value,
                    comment=comment
                )
                db.session.add(rating)
                db.session.commit()
                flash('Rating submitted successfully!', 'success')
                return redirect(url_for('order_history'))
    
    # Get menu items for this order
    menu_items = [item.menu_item for item in order.items]
    return render_template('rate_chef.html', order=order, menu_items=menu_items)

@app.route('/file_complaint', methods=['GET', 'POST'])
@login_required
def file_complaint():
    """File a complaint"""
    if request.method == 'POST':
        filed_against_id = int(request.form.get('filed_against_id'))
        order_id = request.form.get('order_id')
        complaint_type = request.form.get('type')
        description = request.form.get('description')
        
        complaint = Complaint(
            filed_by_id=current_user.id,
            filed_against_id=filed_against_id,
            order_id=int(order_id) if order_id else None,
            type=complaint_type,
            description=description,
            status='Pending'
        )
        db.session.add(complaint)
        db.session.commit()
        
        flash('Complaint filed successfully. Manager will review it.', 'success')
        return redirect(url_for('my_complaints'))
    
    # Get orders for dropdown
    orders = Order.query.filter_by(customer_id=current_user.id).all() if current_user.is_customer() else []
    return render_template('file_complaint.html', orders=orders)

@app.route('/file_compliment', methods=['GET', 'POST'])
@login_required
def file_compliment():
    """File a compliment"""
    if request.method == 'POST':
        filed_against_id = int(request.form.get('filed_against_id'))
        order_id = request.form.get('order_id')
        compliment_type = request.form.get('type')
        description = request.form.get('description')
        
        compliment = Compliment(
            filed_by_id=current_user.id,
            filed_against_id=filed_against_id,
            order_id=int(order_id) if order_id else None,
            type=compliment_type,
            description=description,
            status='Pending'
        )
        db.session.add(compliment)
        db.session.commit()
        
        flash('Compliment submitted successfully!', 'success')
        return redirect(url_for('index'))
    
    orders = Order.query.filter_by(customer_id=current_user.id).all() if current_user.is_customer() else []
    return render_template('file_compliment.html', orders=orders)

@app.route('/my_complaints')
@login_required
def my_complaints():
    """View user's filed complaints"""
    complaints = Complaint.query.filter_by(filed_by_id=current_user.id).order_by(Complaint.created_at.desc()).all()
    return render_template('my_complaints.html', complaints=complaints)

@app.route('/delivery_bid/<int:order_id>', methods=['POST'])
@login_required
@role_required('DeliveryPerson')
def delivery_bid(order_id):
    """Place a bid on an order for delivery"""
    order = Order.query.get_or_404(order_id)
    
    if order.delivery_person_id:
        flash('This order already has a delivery person assigned.', 'warning')
        return redirect(url_for('available_orders'))
    
    bid_amount = request.form.get('bid_amount')
    bid = DeliveryBid(
        order_id=order.id,
        delivery_person_id=current_user.id,
        bid_amount=float(bid_amount) if bid_amount else None,
        status='Pending'
    )
    db.session.add(bid)
    db.session.commit()
    
    flash('Bid placed successfully!', 'success')
    return redirect(url_for('available_orders'))

@app.route('/available_orders')
@login_required
@role_required('DeliveryPerson')
def available_orders():
    """View orders available for bidding"""
    orders = Order.query.filter(
        Order.status.in_(['Ready', 'Pending']),
        Order.delivery_person_id.is_(None)
    ).all()
    return render_template('available_orders.html', orders=orders)

@app.route('/my_deliveries')
@login_required
@role_required('DeliveryPerson')
def my_deliveries():
    """View assigned delivery orders"""
    orders = Order.query.filter_by(delivery_person_id=current_user.id).order_by(Order.timestamp.desc()).all()
    return render_template('my_deliveries.html', orders=orders)

@app.route('/update_order_status/<int:order_id>', methods=['POST'])
@login_required
def update_order_status(order_id):
    """Update order status (for chefs and delivery people)"""
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    
    # Check permissions
    can_update = False
    if current_user.is_manager():
        can_update = True
    elif current_user.is_chef() and order.status in ['Pending', 'Preparing']:
        can_update = True
    elif current_user.is_delivery() and order.delivery_person_id == current_user.id:
        can_update = True
    
    if can_update and new_status in ['Pending', 'Preparing', 'Ready', 'Out for Delivery', 'Delivered']:
        order.status = new_status
        db.session.commit()
        flash(f'Order status updated to {new_status}.', 'success')
    else:
        flash('You do not have permission to update this order.', 'danger')
    
    if current_user.is_delivery():
        return redirect(url_for('my_deliveries'))
    elif current_user.is_chef():
        return redirect(url_for('chef_dashboard'))
    else:
        return redirect(url_for('manager_dashboard'))

@app.route('/chef_dashboard')
@login_required
@role_required('Chef')
def chef_dashboard():
    """Chef dashboard"""
    orders = Order.query.join(OrderItem).join(Menu).filter(
        Menu.chef_id == current_user.id
    ).distinct().order_by(Order.timestamp.desc()).all()
    
    # Get chef's average rating
    ratings = Rating.query.filter_by(chef_id=current_user.id).all()
    avg_rating = round(sum(r.rating for r in ratings) / len(ratings), 2) if ratings else 0.0
    
    return render_template('chef_dashboard.html', orders=orders, avg_rating=avg_rating)

@app.route('/manager_dashboard')
@login_required
@role_required('Manager')
def manager_dashboard():
    """Manager dashboard"""
    pending_registrations = User.query.filter_by(role='Customer', is_active=True).all()
    pending_complaints = Complaint.query.filter_by(status='Pending').all()
    pending_compliments = Compliment.query.filter_by(status='Pending').all()
    pending_orders = Order.query.filter(
        Order.status.in_(['Ready', 'Pending']),
        Order.delivery_person_id.is_(None)
    ).all()
    flagged_kb = KnowledgeBaseEntry.query.filter_by(flagged=True).all()
    
    # Get all delivery bids
    bids = DeliveryBid.query.filter_by(status='Pending').all()
    
    return render_template('manager_dashboard.html',
                         pending_registrations=pending_registrations,
                         pending_complaints=pending_complaints,
                         pending_compliments=pending_compliments,
                         pending_orders=pending_orders,
                         flagged_kb=flagged_kb,
                         bids=bids)

@app.route('/review_complaint/<int:complaint_id>', methods=['POST'])
@login_required
@role_required('Manager')
def review_complaint(complaint_id):
    """Manager reviews and decides on complaint"""
    decision = request.form.get('decision')
    notes = request.form.get('notes', '')
    
    process_complaint_decision(complaint_id, decision, notes)
    flash(f'Complaint {decision.lower()}ed.', 'success')
    return redirect(url_for('manager_dashboard'))

@app.route('/review_compliment/<int:compliment_id>', methods=['POST'])
@login_required
@role_required('Manager')
def review_compliment(compliment_id):
    """Manager reviews compliment"""
    compliment = Compliment.query.get_or_404(compliment_id)
    decision = request.form.get('decision')
    notes = request.form.get('notes', '')
    
    compliment.status = decision
    compliment.manager_decision = decision
    compliment.manager_notes = notes
    compliment.reviewed_at = datetime.utcnow()
    db.session.commit()
    
    flash('Compliment reviewed.', 'success')
    return redirect(url_for('manager_dashboard'))

@app.route('/assign_order/<int:order_id>', methods=['POST'])
@login_required
@role_required('Manager')
def assign_order(order_id):
    """Manager assigns order to delivery person based on bids"""
    order = Order.query.get_or_404(order_id)
    delivery_person_id = int(request.form.get('delivery_person_id'))
    
    order.delivery_person_id = delivery_person_id
    order.status = 'Out for Delivery'
    
    # Mark bid as accepted
    bid = DeliveryBid.query.filter_by(order_id=order.id, delivery_person_id=delivery_person_id).first()
    if bid:
        bid.status = 'Accepted'
    
    # Reject other bids
    DeliveryBid.query.filter_by(order_id=order.id, status='Pending').update({'status': 'Rejected'})
    
    db.session.commit()
    flash('Order assigned successfully.', 'success')
    return redirect(url_for('manager_dashboard'))

@app.route('/hr_management')
@login_required
@role_required('Manager')
def hr_management():
    """HR management page"""
    employees = User.query.filter(User.role.in_(['Chef', 'DeliveryPerson'])).all()
    blacklisted = Blacklist.query.all()
    return render_template('hr_management.html', employees=employees, blacklisted=blacklisted)

@app.route('/hire_fire/<int:user_id>', methods=['POST'])
@login_required
@role_required('Manager')
def hire_fire(user_id):
    """Hire or fire employee"""
    user = User.query.get_or_404(user_id)
    action = request.form.get('action')
    
    if action == 'fire':
        user.is_active = False
        flash(f'{user.username} has been fired.', 'success')
    elif action == 'hire':
        user.is_active = True
        flash(f'{user.username} has been hired/reactivated.', 'success')
    
    db.session.commit()
    return redirect(url_for('hr_management'))

@app.route('/adjust_salary/<int:user_id>', methods=['POST'])
@login_required
@role_required('Manager')
def adjust_salary(user_id):
    """Adjust employee salary"""
    user = User.query.get_or_404(user_id)
    new_salary = float(request.form.get('salary', 0))
    
    user.salary = new_salary
    db.session.commit()
    flash(f'Salary for {user.username} updated to ${new_salary:.2f}.', 'success')
    return redirect(url_for('hr_management'))

@app.route('/manage_knowledge_base')
@login_required
@role_required('Manager')
def manage_knowledge_base():
    """Manage knowledge base entries"""
    entries = KnowledgeBaseEntry.query.order_by(KnowledgeBaseEntry.flagged.desc(), KnowledgeBaseEntry.created_at.desc()).all()
    return render_template('manage_knowledge_base.html', entries=entries)

@app.route('/remove_kb_entry/<int:entry_id>', methods=['POST'])
@login_required
@role_required('Manager')
def remove_kb_entry(entry_id):
    """Remove knowledge base entry"""
    entry = KnowledgeBaseEntry.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    flash('Knowledge base entry removed.', 'success')
    return redirect(url_for('manage_knowledge_base'))

@app.route('/unflag_kb_entry/<int:entry_id>', methods=['POST'])
@login_required
@role_required('Manager')
def unflag_kb_entry(entry_id):
    """Unflag knowledge base entry"""
    entry = KnowledgeBaseEntry.query.get_or_404(entry_id)
    entry.flagged = False
    db.session.commit()
    flash('Knowledge base entry unflagged.', 'success')
    return redirect(url_for('manage_knowledge_base'))

@app.route('/ai_chat', methods=['GET', 'POST'])
def ai_chat():
    """AI customer service chat"""
    if request.method == 'POST':
        query = request.form.get('query')
        if query:
            ai_service = get_ai_service()
            user_id = current_user.id if current_user.is_authenticated else None
            response = ai_service.get_ai_response(query, user_id)
            return jsonify(response)
    
    return render_template('ai_chat.html')

@app.route('/rate_ai_response/<int:rating_id>', methods=['POST'])
def rate_ai_response(rating_id):
    """Rate an AI response"""
    try:
        rating_value = int(request.form.get('rating', 0))
        if rating_value < 0 or rating_value > 5:
            flash('Invalid rating value.', 'danger')
            return redirect(url_for('ai_chat'))
        
        ai_service = get_ai_service()
        
        if ai_service.rate_ai_response(rating_id, rating_value):
            flash('Thank you for your feedback!', 'success')
        else:
            flash('Failed to submit rating.', 'danger')
    except Exception as e:
        flash(f'Error submitting rating: {str(e)}', 'danger')
    
    return redirect(url_for('ai_chat'))

if __name__ == '__main__':
    app.run(debug=True)

