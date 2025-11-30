from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app.models import MenuItem, Category, Order, User, Coupon, DeliveryZone
from app import db
import os
from werkzeug.utils import secure_filename
from flask import current_app
from app.utils.email import send_order_status_update_email
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime



bp = Blueprint('admin', __name__)

@bp.before_request
@login_required
def require_admin():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('main.index'))

@bp.route('/users')
@login_required
def users():
    if not current_user.is_admin:
        flash("Access denied", "danger")
        return redirect(url_for('main.index'))

    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)


@bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if not current_user.is_admin:
        flash("Access denied", "danger")
        return redirect(url_for('main.index'))

    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        user.first_name = request.form.get('first_name')
        user.last_name = request.form.get('last_name')
        user.email = request.form.get('email')
        user.phone = request.form.get('phone')
        user.address = request.form.get('address')
        user.is_admin = True if request.form.get('role') == 'admin' else False

        # Optional password change
        new_password = request.form.get('password')
        if new_password:
            user.password_hash = generate_password_hash(new_password)

        db.session.commit()
        flash("User updated successfully!", "success")
        return redirect(url_for('admin.users'))

    return render_template('admin/edit_user.html', user=user)


@bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        flash("Access denied", "danger")
        return redirect(url_for('main.index'))

    user = User.query.get_or_404(user_id)

    # Safety rules
    if user.id == current_user.id:
        flash("You cannot delete your own account!", "warning")
        return redirect(url_for('admin.users'))

    if user.is_admin:
        flash("You cannot delete another admin!", "danger")
        return redirect(url_for('admin.users'))

    db.session.delete(user)
    db.session.commit()

    flash("User deleted successfully!", "success")
    return redirect(url_for('admin.users'))



@bp.route('/dashboard')
def dashboard():
    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(status='pending').count()
    total_users = User.query.count()
    total_items = MenuItem.query.count()
    
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html', 
                         total_orders=total_orders,
                         pending_orders=pending_orders,
                         total_users=total_users,
                         total_items=total_items,
                         recent_orders=recent_orders)

@bp.route('/menu_management')
def menu_management():
    items = MenuItem.query.all()
    categories = Category.query.all()
    return render_template('admin/menu_management.html', items=items, categories=categories)



@bp.route('/add_menu_item', methods=['POST'])
def add_menu_item():
    name = request.form.get('name')
    description = request.form.get('description')
    price = float(request.form.get('price'))
    category_id = int(request.form.get('category_id'))
    preparation_time = int(request.form.get('preparation_time', 15))

    # --- IMAGE UPLOAD HANDLING ---
    image = request.files.get('image')
    image_filename = None

    if image and image.filename != "":
        filename = secure_filename(image.filename)
        image_path = os.path.join(current_app.root_path, 'static/images/menu', filename)
        image.save(image_path)
        image_filename = filename

    item = MenuItem(
        name=name,
        description=description,
        price=price,
        category_id=category_id,
        preparation_time=preparation_time,
        image_url=image_filename
    )

    db.session.add(item)
    db.session.commit()

    flash('Menu item added successfully!', 'success')
    return redirect(url_for('admin.menu_management'))


# @bp.route('/edit_menu_item/<int:item_id>', methods=['POST'])
# def edit_menu_item(item_id):
#     item = MenuItem.query.get_or_404(item_id)
    
#     item.name = request.form.get('name')
#     item.description = request.form.get('description')
#     item.price = float(request.form.get('price'))
#     item.category_id = int(request.form.get('category_id'))
#     item.preparation_time = int(request.form.get('preparation_time'))
#     item.is_available = 'is_available' in request.form
    
#     db.session.commit()
    
#     flash('Menu item updated successfully!', 'success')
#     return redirect(url_for('admin.menu_management'))

@bp.route('/edit_menu_item/<int:item_id>', methods=['POST'])
def edit_menu_item(item_id):
    item = MenuItem.query.get_or_404(item_id)

    item.name = request.form.get('name')
    item.description = request.form.get('description')
    item.price = float(request.form.get('price'))
    item.category_id = int(request.form.get('category_id'))
    item.preparation_time = int(request.form.get('preparation_time'))
    item.is_available = 'is_available' in request.form

    # --- CHECK IF NEW IMAGE WAS UPLOADED ---
    new_image = request.files.get('image')

    if new_image and new_image.filename != "":
        filename = secure_filename(new_image.filename)
        image_path = os.path.join(current_app.root_path, 'static/images/menu', filename)
        new_image.save(image_path)
        item.image_url = filename

    db.session.commit()

    flash('Menu item updated successfully!', 'success')
    return redirect(url_for('admin.menu_management'))

@bp.route('/delete_menu_item/<int:item_id>', methods=['POST'])
def delete_menu_item(item_id):
    item = MenuItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Menu item deleted successfully!', 'success')
    return redirect(url_for('admin.menu_management'))

@bp.route('/orders')
def orders():
    # Get filter parameters
    status = request.args.get('status')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    query = Order.query
    
    if status:
        query = query.filter_by(status=status)
    
    if date_from:
        query = query.filter(Order.created_at >= date_from)
    
    if date_to:
        query = query.filter(Order.created_at <= date_to)
    
    orders = query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)


# @bp.route('/update_order_status/<int:order_id>', methods=['POST'])
# def update_order_status(order_id):
#     order = Order.query.get_or_404(order_id)
#     new_status = request.form.get('status')
    
#     order.status = new_status
#     db.session.commit()
    
#     flash(f'Order {order.order_number} status updated to {new_status}', 'success')
#     return redirect(url_for('admin.orders'))


@bp.route('/update_order_status/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')

    if not new_status:
        flash('No status provided.', 'warning')
        return redirect(url_for('admin.orders'))

    old_status = order.status or 'unknown'

    if new_status == old_status:
        flash(f'Order {order.order_number} is already in status "{new_status}".', 'info')
        return redirect(url_for('admin.orders'))

    order.status = new_status
    try:
        db.session.commit()
    except:
        db.session.rollback()
        flash('Failed to update order status.', 'danger')
        return redirect(url_for('admin.orders'))

    # Now send the notification email
    email_sent = send_order_status_update_email(order, old_status, new_status)

    if email_sent:
        flash(f'Order {order.order_number} status updated and customer notified.', 'success')
    else:
        flash(f'Order updated but failed to send notification email.', 'warning')

    return redirect(url_for('admin.orders'))


# @bp.route('/delete_order/<int:order_id>', methods=['POST'])
# def delete_order(order_id):
#     order = Order.query.get_or_404(order_id)
#     db.session.delete(order)
#     db.session.commit()
#     flash('Order deleted successfully!', 'success')
#     return redirect(url_for('admin.orders'))


@bp.route('/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    order = Order.query.get_or_404(order_id)

    # ❌ Prevent deleting paid orders
    if order.payment_status == 'paid':
        flash('Paid orders cannot be deleted. You may only cancel or archive them.', 'danger')
        return redirect(url_for('admin.orders'))

    # Proceed to delete
    db.session.delete(order)
    db.session.commit()

    flash('Order deleted successfully!', 'success')
    return redirect(url_for('admin.orders'))



@bp.route("/order_items/<int:order_id>")
@login_required
def order_items_modal(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template("admin/modals/order_items_modal.html", order=order)


@bp.route("/order_details/<int:order_id>")
@login_required
def order_details_modal(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template("admin/modals/order_details_modal.html", order=order)





@bp.route('/coupons')
@login_required
def coupons_list():
    # ensure current_user.is_admin check in real app
    coupons = Coupon.query.order_by(Coupon.created_at.desc()).all()
    return render_template('admin/coupons/list.html', coupons=coupons)

# @bp.route('/coupons/create', methods=['GET', 'POST'])
# @login_required
# def coupon_create():
#     if request.method == 'POST':
#         code = request.form.get('code', '').strip().upper()
#         coupon_type = request.form.get('coupon_type', 'percent')
#         amount = float(request.form.get('amount', 0))
#         starts_at = request.form.get('starts_at') or None
#         expires_at = request.form.get('expires_at') or None
#         min_subtotal = request.form.get('min_subtotal') or None
#         max_uses = request.form.get('max_uses') or None
#         max_uses_per_user = request.form.get('max_uses_per_user') or None
#         selected_zones = request.form.getlist('zones')
#         note = request.form.get('note')
        
#         for zid in selected_zones:
#             zone = DeliveryZone.query.get(int(zid))
#             if zone:
#                 coupon.zones.append(zone)

#         # parse datetimes
#         if starts_at:
#             starts_at = datetime.fromisoformat(starts_at)
#         if expires_at:
#             expires_at = datetime.fromisoformat(expires_at)

#         # validation
#         if not code:
#             flash('Coupon code is required', 'danger')
#             return redirect(url_for('admin.coupon_create'))

#         # uniqueness
#         if Coupon.query.filter_by(code=code).first():
#             flash('A coupon with that code already exists', 'danger')
#             return redirect(url_for('admin.coupon_create'))

#         coupon = Coupon(
#             code=code,
#             coupon_type=coupon_type,
#             amount=amount,
#             starts_at=starts_at,
#             expires_at=expires_at,
#             min_subtotal=float(min_subtotal) if min_subtotal else None,
#             max_uses=int(max_uses) if max_uses else None,
#             max_uses_per_user=int(max_uses_per_user) if max_uses_per_user else None,
#             is_active=True,
#             created_by=current_user.id,
#             note=note
#         )
#         db.session.add(coupon)
#         db.session.commit()
#         flash('Coupon created', 'success')
#         return redirect(url_for('admin.coupons_list'))

#     return render_template('admin/coupons/create.html')


@bp.route('/coupons/create', methods=['GET', 'POST'])
@login_required
def coupon_create():
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        coupon_type = request.form.get('coupon_type', 'percent')
        amount = float(request.form.get('amount', 0))

        starts_at = request.form.get('starts_at') or None
        expires_at = request.form.get('expires_at') or None

        min_subtotal = request.form.get('min_subtotal') or None
        max_uses = request.form.get('max_uses') or None
        max_uses_per_user = request.form.get('max_uses_per_user') or None

        selected_zones = request.form.getlist('zones')
        note = request.form.get('note')

        # Parse datetime
        if starts_at:
            starts_at = datetime.fromisoformat(starts_at)
        if expires_at:
            expires_at = datetime.fromisoformat(expires_at)

        # Validation
        if not code:
            flash('Coupon code is required', 'danger')
            return redirect(url_for('admin.coupon_create'))

        # Uniqueness check
        if Coupon.query.filter_by(code=code).first():
            flash('A coupon with that code already exists', 'danger')
            return redirect(url_for('admin.coupon_create'))

        # Create coupon record
        coupon = Coupon(
            code=code,
            coupon_type=coupon_type,
            amount=amount,
            starts_at=starts_at,
            expires_at=expires_at,
            min_subtotal=float(min_subtotal) if min_subtotal else None,
            max_uses=int(max_uses) if max_uses else None,
            max_uses_per_user=int(max_uses_per_user) if max_uses_per_user else None,
            is_active=True,
            created_by=current_user.id,
            note=note
        )

        db.session.add(coupon)
        db.session.flush()   # make coupon.id available

        # Assign delivery zones
        for zid in selected_zones:
            zone = DeliveryZone.query.get(int(zid))
            if zone:
                coupon.zones.append(zone)

        db.session.commit()

        flash('Coupon created', 'success')
        return redirect(url_for('admin.coupons_list'))

    zones = DeliveryZone.query.order_by(DeliveryZone.name).all()
    return render_template('admin/coupons/create.html', zones=zones)




@bp.route('/coupons/delete/<int:coupon_id>', methods=['POST'])
@login_required
def coupon_delete(coupon_id):
    coupon = Coupon.query.get_or_404(coupon_id)
    db.session.delete(coupon)
    db.session.commit()
    flash("Coupon deleted successfully", "success")
    return redirect(url_for('admin.coupons_list'))


@bp.route('/coupons/toggle/<int:coupon_id>', methods=['POST'])
@login_required
def coupon_toggle(coupon_id):
    coupon = Coupon.query.get_or_404(coupon_id)
    coupon.is_active = not coupon.is_active
    db.session.commit()

    flash(f"Coupon {'activated' if coupon.is_active else 'deactivated'}", "success")
    return redirect(url_for('admin.coupons_list'))



@bp.route('/coupons/edit/<int:coupon_id>', methods=['GET', 'POST'])
@login_required
def coupon_edit(coupon_id):
    # Make sure only admin can access (optional)
    # if not current_user.is_admin:
    #     abort(403)

    coupon = Coupon.query.get_or_404(coupon_id)
    zones = DeliveryZone.query.order_by(DeliveryZone.name).all()

    # Preload selected zone IDs for the template
    selected_zones = [z.id for z in coupon.zones]

    if request.method == 'POST':
        coupon.coupon_type = request.form.get('coupon_type', 'percent')
        coupon.amount = float(request.form.get('amount', 0))

        starts_at = request.form.get('starts_at') or None
        expires_at = request.form.get('expires_at') or None

        if starts_at:
            coupon.starts_at = datetime.fromisoformat(starts_at)
        else:
            coupon.starts_at = None

        if expires_at:
            coupon.expires_at = datetime.fromisoformat(expires_at)
        else:
            coupon.expires_at = None

        min_subtotal = request.form.get('min_subtotal')
        coupon.min_subtotal = float(min_subtotal) if min_subtotal else None

        max_uses = request.form.get('max_uses')
        coupon.max_uses = int(max_uses) if max_uses else None

        max_uses_per_user = request.form.get('max_uses_per_user')
        coupon.max_uses_per_user = int(max_uses_per_user) if max_uses_per_user else None

        coupon.note = request.form.get('note')

        # Update delivery zone restrictions
        coupon.zones.clear()
        selected = request.form.getlist('zones')
        for zid in selected:
            zone = DeliveryZone.query.get(int(zid))
            if zone:
                coupon.zones.append(zone)

        db.session.commit()
        flash('Coupon updated successfully', 'success')
        return redirect(url_for('admin.coupons_list'))

    return render_template(
        'admin/coupons/edit.html',
        coupon=coupon,
        zones=zones,
        selected_zones=selected_zones
    )
