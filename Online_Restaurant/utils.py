from models import db, User, Order, Complaint, Warning, Blacklist
from sqlalchemy import func
from datetime import datetime

def calculate_vip_status(user_id):
    """
    Check if user qualifies for VIP status:
    - Total spending > $100 OR
    - 3 orders without complaints
    Auto-promote if criteria met.
    """
    user = db.session.get(User, user_id)
    if not user or user.role in ['Chef', 'DeliveryPerson', 'Manager']:
        return False
    
    # Check if already VIP
    if user.role == 'VIP':
        return True
    
    # Check total spending
    total_spent = db.session.query(func.sum(Order.total_amount)).filter(
        Order.customer_id == user_id,
        Order.status == 'Delivered'
    ).scalar() or 0.0
    
    if total_spent > 100.0:
        user.role = 'VIP'
        db.session.commit()
        return True
    
    # Check for 3 orders without complaints
    delivered_orders = Order.query.filter(
        Order.customer_id == user_id,
        Order.status == 'Delivered'
    ).all()
    
    if len(delivered_orders) >= 3:
        # Check if any of these orders have approved complaints
        order_ids = [o.id for o in delivered_orders]
        approved_complaints = Complaint.query.filter(
            Complaint.order_id.in_(order_ids),
            Complaint.status == 'Approved'
        ).count()
        
        if approved_complaints == 0:
            user.role = 'VIP'
            db.session.commit()
            return True
    
    return False

def process_complaint_decision(complaint_id, manager_decision, manager_notes=None):
    """
    Process manager's decision on a complaint.
    If rejected: issue warning to filer
    Count warnings: 2 warnings (VIP) = demote, 3 warnings (any) = blacklist
    """
    complaint = db.session.get(Complaint, complaint_id)
    if not complaint:
        return False
    
    complaint.status = 'Approved' if manager_decision == 'Approved' else 'Rejected'
    complaint.manager_decision = manager_decision
    complaint.manager_notes = manager_notes
    complaint.reviewed_at = datetime.utcnow()
    
    # If complaint is rejected, issue warning to the person who filed it
    if manager_decision == 'Rejected':
        warning = Warning(
            user_id=complaint.filed_by_id,
            reason=f"Rejected complaint: {complaint.description[:100]}",
            complaint_id=complaint_id
        )
        db.session.add(warning)
        
        # Count warnings for the user
        warning_count = Warning.query.filter_by(user_id=complaint.filed_by_id).count()
        filer = db.session.get(User, complaint.filed_by_id)
        
        # Check if user should be demoted or blacklisted
        if warning_count >= 3:
            # Blacklist user
            blacklist_entry = Blacklist(
                user_id=complaint.filed_by_id,
                reason=f"3 warnings issued for rejected complaints"
            )
            db.session.add(blacklist_entry)
            filer.is_active = False
        
        elif warning_count >= 2 and filer.role == 'VIP':
            # Demote VIP to Customer
            filer.role = 'Customer'
    
    db.session.commit()
    return True

def get_user_warning_count(user_id):
    """Get the number of warnings for a user."""
    return Warning.query.filter_by(user_id=user_id).count()

def is_user_blacklisted(user_id):
    """Check if a user is blacklisted."""
    return Blacklist.query.filter_by(user_id=user_id).first() is not None

def get_user_total_spending(user_id):
    """Calculate total amount spent by a user."""
    total = db.session.query(func.sum(Order.total_amount)).filter(
        Order.customer_id == user_id,
        Order.status == 'Delivered'
    ).scalar() or 0.0
    return float(total)

def get_user_order_count(user_id):
    """Get total number of delivered orders for a user."""
    return Order.query.filter(
        Order.customer_id == user_id,
        Order.status == 'Delivered'
    ).count()

def can_user_place_order(user_id):
    """Check if user can place an order (not blacklisted, has sufficient balance, etc.)"""
    if is_user_blacklisted(user_id):
        return False, "You are blacklisted and cannot place orders."
    
    user = db.session.get(User, user_id)
    if not user or not user.is_active:
        return False, "Your account is not active."
    
    return True, None

