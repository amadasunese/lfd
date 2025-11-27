from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from app.models import MenuItem, Order, OrderItem
from app import db
import os
from werkzeug.utils import secure_filename
from datetime import timedelta

bp = Blueprint('utils', __name__)

# Allowed file extensions for uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/upload_image', methods=['POST'])
@login_required
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Add timestamp to make filename unique
        timestamp = str(int(os.time()))
        filename = f"{timestamp}_{filename}"
        
        # Create upload directory if it doesn't exist
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'menu_items')
        os.makedirs(upload_dir, exist_ok=True)
        
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)
        
        # Return relative path for database storage
        image_url = f"/static/uploads/menu_items/{filename}"
        return jsonify({'success': True, 'image_url': image_url})
    
    return jsonify({'error': 'Invalid file type'}), 400

@bp.route('/search_suggestions')
def search_suggestions():
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    
    suggestions = MenuItem.query.filter(
        MenuItem.name.ilike(f'%{query}%') |
        MenuItem.description.ilike(f'%{query}%')
    ).filter_by(is_available=True).limit(5).all()
    
    return jsonify([{
        'id': item.id,
        'name': item.name,
        'price': item.price,
        'image_url': item.image_url
    } for item in suggestions])



@bp.route('/order_tracking/<order_number>')
def order_tracking(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    
    # Calculate estimated delivery time
    estimated_delivery = order.created_at + timedelta(minutes=order.preparation_time + 15)
    
    return jsonify({
        'order_number': order.order_number,
        'status': order.status,
        'created_at': order.created_at.isoformat(),
        'estimated_delivery': estimated_delivery.isoformat(),
        'total_amount': order.total_amount,
        'items_count': order.order_items.count()
    })

@bp.route('/popular_items')
def popular_items():
    # Get most ordered items in the last 30 days
    from datetime import datetime, timedelta
    
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    popular_items = db.session.query(MenuItem, db.func.count(OrderItem.id).label('order_count'))\
        .join(OrderItem)\
        .join(Order)\
        .filter(Order.created_at >= thirty_days_ago)\
        .group_by(MenuItem)\
        .order_by(db.func.count(OrderItem.id).desc())\
        .limit(6)\
        .all()
    
    return jsonify([{
        'id': item.MenuItem.id,
        'name': item.MenuItem.name,
        'price': item.MenuItem.price,
        'image_url': item.MenuItem.image_url,
        'order_count': item.order_count
    } for item in popular_items])

@bp.route('/customer_stats')
@login_required
def customer_stats():
    total_orders = current_user.orders.count()
    total_spent = db.session.query(db.func.sum(Order.total_amount))\
        .filter_by(customer_id=current_user.id)\
        .scalar() or 0
    
    favorite_items = db.session.query(MenuItem, db.func.count(OrderItem.id).label('order_count'))\
        .join(OrderItem)\
        .join(Order)\
        .filter(Order.customer_id == current_user.id)\
        .group_by(MenuItem)\
        .order_by(db.func.count(OrderItem.id).desc())\
        .limit(3)\
        .all()
    
    return jsonify({
        'total_orders': total_orders,
        'total_spent': float(total_spent),
        'favorite_items': [{
            'id': item.MenuItem.id,
            'name': item.MenuItem.name,
            'order_count': item.order_count
        } for item in favorite_items]
    })