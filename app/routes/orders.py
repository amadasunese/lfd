# order.py
import time
from uuid import uuid4
from flask import Blueprint, render_template, request, flash, redirect, url_for, session, current_app, jsonify
from flask_login import login_required, current_user
from app.models import Order, OrderItem, MenuItem, DeliveryZone, Coupon, CouponUsage
from app.models import db
from datetime import datetime, timedelta
from app.utils.email import send_order_confirmation_email, send_order_status_update_email
from app.utils.paystack import init_payment  # your wrapper to create checkout
from paystackapi.transaction import Transaction
import hmac, hashlib
from app.utils.delivery import get_delivery_fee

bp = Blueprint('orders', __name__)

# --- CART VIEWS ---
@bp.route('/cart')
@login_required
def cart():
    return render_template('cart.html')


@bp.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    item_id = request.form.get('item_id')
    quantity = int(request.form.get('quantity', 1))
    item = MenuItem.query.get_or_404(item_id)

    cart = session.get('cart', {})
    if str(item_id) in cart:
        cart[str(item_id)]['quantity'] += quantity
    else:
        cart[str(item_id)] = {
            'name': item.name,
            'price': float(item.price),
            'quantity': quantity
        }
    session['cart'] = cart
    cart_count = sum(i['quantity'] for i in cart.values())

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': f'{item.name} added', 'cart_count': cart_count}), 200

    flash(f'{item.name} added to cart!', 'success')
    return redirect(url_for('menu.menu'))


@bp.route('/update_cart', methods=['POST'])
@login_required
def update_cart():
    item_id = request.form.get('item_id')
    quantity = int(request.form.get('quantity', 1))
    if 'cart' not in session:
        session['cart'] = {}
    cart = session['cart']
    if quantity > 0:
        cart[item_id]['quantity'] = quantity
    else:
        cart.pop(item_id, None)
    session['cart'] = cart
    flash('Cart updated!', 'success')
    return redirect(url_for('orders.cart'))


@bp.route('/remove_from_cart', methods=['POST'])
@login_required
def remove_from_cart():
    item_id = request.form.get('item_id')
    if 'cart' in session:
        session['cart'].pop(item_id, None)
        session['cart'] = session['cart']
    flash('Item removed from cart!', 'success')
    return redirect(url_for('orders.cart'))


# --- COUPONS ---
def apply_coupon(code, subtotal, delivery_zone_id=None, user=None):
    """
    Return (discount_amount, message, coupon)
    """
    if not code:
        return 0.0, "No coupon provided", None

    code = code.strip().upper()
    coupon = Coupon.query.filter_by(code=code).first()
    now = datetime.utcnow()

    if not coupon:
        return 0.0, "Invalid coupon code", None

    if not coupon.is_active:
        return 0.0, "This coupon is inactive", coupon

    if coupon.starts_at and now < coupon.starts_at:
        return 0.0, f"This coupon is not active until {coupon.starts_at}", coupon

    if coupon.expires_at and now > coupon.expires_at:
        return 0.0, "This coupon has expired", coupon

    if coupon.min_subtotal and subtotal < coupon.min_subtotal:
        return 0.0, f"Order must be at least ₦{coupon.min_subtotal:.2f} to use this coupon", coupon

    if coupon.max_uses is not None and coupon.uses_count >= coupon.max_uses:
        return 0.0, "This coupon has reached its maximum number of uses", coupon

    if coupon.zones:
        allowed_zone_ids = [z.id for z in coupon.zones]
        if delivery_zone_id not in allowed_zone_ids:
            return 0.0, "Coupon not valid for this delivery area", coupon

    if user and coupon.max_uses_per_user is not None:
        used_count = CouponUsage.query.filter_by(coupon_id=coupon.id, user_id=user.id).count()
        if used_count >= coupon.max_uses_per_user:
            return 0.0, "You have already used this coupon the maximum allowed times", coupon

    if coupon.coupon_type == 'percent':
        discount = subtotal * (coupon.amount / 100.0)
    else:
        discount = float(coupon.amount)

    discount = min(discount, subtotal)
    message = f"{int(coupon.amount)}% off" if coupon.coupon_type == 'percent' else f"₦{coupon.amount:.2f} off"
    return discount, message, coupon


@bp.route('/apply-coupon', methods=['POST'])
@login_required
def apply_coupon_api():
    data = request.get_json()
    code = data.get("code", "").strip()
    subtotal = float(data.get("subtotal", 0))
    delivery_zone_id = data.get("delivery_zone_id")  # may be None
    if delivery_zone_id:
        try:
            delivery_zone_id = int(delivery_zone_id)
        except Exception:
            delivery_zone_id = None

    discount, message, coupon = apply_coupon(code, subtotal, delivery_zone_id, current_user)
    return jsonify({"valid": discount > 0, "discount": discount, "message": message})


# --- helpers ---
def get_estimated_time(zone_identifier):
    if not zone_identifier:
        return "30–50 mins"
    try:
        zone_id = int(zone_identifier)
        zone = DeliveryZone.query.get(zone_id)
    except Exception:
        zone_name = str(zone_identifier).lower()
        zone = DeliveryZone.query.filter(DeliveryZone.name.ilike(f"%{zone_name}%")).first()

    if zone and zone.eta:
        return zone.eta

    name = (zone.name.lower() if zone else "")
    DEFAULTS = {
        "gra": "20–30 mins",
        "ugbowo": "25–40 mins",
        "use": "15–25 mins",
    }
    for key, t in DEFAULTS.items():
        if key in name:
            return t
    return "30–50 mins"


# ---------- CREATE ORDER (do NOT clear cart here) ----------
@bp.route('/checkout/create', methods=['POST'])
@login_required
def create_order():
    cart = session.get("cart", {})
    if not cart:
        flash("Your cart is empty", "warning")
        return redirect(url_for("menu.menu"))

    subtotal = sum(d["price"] * d["quantity"] for d in cart.values())

    delivery_zone_id = request.form.get("delivery_zone")
    delivery_zone = DeliveryZone.query.get(int(delivery_zone_id)) if delivery_zone_id else None
    delivery_fee = delivery_zone.fee if delivery_zone else get_delivery_fee(request.form.get('delivery_address', ''))

    coupon_code = request.form.get("coupon_code", "").strip()
    discount = 0
    applied_coupon = None
    if coupon_code:
        discount, msg, applied_coupon = apply_coupon(coupon_code, subtotal, int(delivery_zone_id) if delivery_zone_id else None, current_user)
        if discount <= 0:
            flash(msg, "warning")

    tax = subtotal * 0.075
    total = subtotal + delivery_fee + tax - discount
    total = max(total, 0)

    order = Order(
        order_number=f"LFD{uuid4().hex[:10].upper()}",
        customer_id=current_user.id,
        subtotal_amount=subtotal,
        discount_amount=discount,
        delivery_fee=delivery_fee,
        total_amount=total,
        delivery_zone_id=delivery_zone.id if delivery_zone else None,
        delivery_address=request.form.get("delivery_address", "").strip(),
        phone_number=request.form.get("phone_number", ""),
        notes=request.form.get("notes", ""),
        coupon_id=applied_coupon.id if applied_coupon else None,
        status="pending",
        payment_method="pending",
        payment_status="pending",
    )

    db.session.add(order)
    db.session.flush()

    for item_id, d in cart.items():
        menu_item = MenuItem.query.get(int(item_id))
        if not menu_item:
            continue
        oi = OrderItem(
            order_id=order.id,
            menu_item_id=menu_item.id,
            quantity=d["quantity"],
            unit_price=d["price"],
            subtotal=d["quantity"] * d["price"]
        )
        db.session.add(oi)

    if applied_coupon:
        applied_coupon.uses_count = (applied_coupon.uses_count or 0) + 1
        db.session.add(CouponUsage(coupon_id=applied_coupon.id, user_id=current_user.id, order_id=order.id))

    db.session.commit()
    
    # EMAIL
    try:
        send_order_confirmation_email(order)
    except Exception as e:
        current_app.logger.error(f"Failed to send order confirmation email: {e}")

    # DO NOT clear the cart here — wait until payment confirmed (webhook/callback or COD confirmation)
    flash("Order created – choose payment method", "info")
    return redirect(url_for("orders.checkout", order_id=order.id))


# ---------- CHECKOUT VIEW ----------
@bp.route('/checkout', methods=['GET'])
@login_required
def checkout():
    order_id = request.args.get("order_id", type=int)
    order = Order.query.get(order_id) if order_id else None

    zones = DeliveryZone.query.order_by(DeliveryZone.name).all()

    if order:
        items = order.order_items.all()   # dynamic relationship needs .all()
        delivery_fee = order.delivery_fee
        subtotal = order.subtotal_amount
        discount = order.discount_amount
    else:
        cart = session.get("cart", {})
        items = list(cart.items())
        subtotal = sum(d["price"] * d["quantity"] for d in cart.values())
        discount = 0
        delivery_fee = 0

    estimated_time = order.delivery_zone.eta if order and order.delivery_zone else None

    return render_template(
        "checkout.html",
        order=order,
        items=items,
        zones=zones,
        subtotal=subtotal,
        discount=discount,
        delivery_fee=delivery_fee,
        estimated_time=estimated_time,
        delivery_address=current_user.address
    )


# ---------- PAYMENT (Paystack) ----------
@bp.route('/checkout/pay', methods=['POST'])
@login_required
def pay_with_paystack():
    order = Order.query.get_or_404(request.form.get('order_id'))
    if order.customer_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('orders.my_orders'))

    result = init_payment(order, current_user)
    if not result:
        flash('Gateway error – try again', 'warning')
        return redirect(url_for('orders.checkout', order_id=order.id))

    if isinstance(result, dict):
        checkout_url = result.get('authorization_url') or result.get('url')
        reference = result.get('reference') or result.get('ref')
    else:
        checkout_url = result
        reference = None

    if reference:
        order.paystack_ref = reference
        db.session.commit()

    if checkout_url:
        return redirect(checkout_url)

    flash('Gateway error – try again', 'warning')
    return redirect(url_for('orders.checkout', order_id=order.id))


# Paystack return (user redirect)
@bp.route('/pay/callback')
@login_required
def paystack_callback():
    ref = request.args.get('reference')
    if not ref:
        flash('No reference returned', 'warning')
        return redirect(url_for('orders.my_orders'))

    resp = Transaction.verify(reference=ref)
    if resp['status'] and resp['data']['status'] == 'success':
        order = Order.query.filter_by(paystack_ref=ref).first_or_404()
        old_status = order.status
        order.status = 'confirmed'
        order.payment_status = 'paid'
        order.payment_method = 'paystack'
        order.updated_at = datetime.utcnow()
        db.session.commit()

        # Clear cart only after payment confirmed
        session.pop('cart', None)

        try:
            send_order_status_update_email(order, old_status, 'confirmed')
        except Exception as e:
            current_app.logger.error(f"Status email failed: {e}")

        flash('Payment successful! Your order is confirmed.', 'success')
        return redirect(url_for('orders.order_confirmation', order_id=order.id))

    flash('Payment failed or cancelled', 'warning')
    return redirect(url_for('orders.my_orders'))


# Paystack webhook (server-to-server)
@bp.route('/pay/webhook', methods=['POST'])
def paystack_webhook():
    sig = request.headers.get('x-paystack-signature')
    computed_sig = hmac.new(current_app.config['PAYSTACK_SECRET_KEY'].encode(), request.data, hashlib.sha512).hexdigest()
    if computed_sig != sig:
        return 'invalid signature', 400

    event = request.get_json()
    if event.get('event') == 'charge.success':
        ref = event['data']['reference']
        order = Order.query.filter_by(paystack_ref=ref).first()
        if order and order.payment_status != 'paid':
            old_status = order.status
            order.payment_status = 'paid'
            order.payment_method = 'paystack'
            order.status = 'confirmed'
            order.updated_at = datetime.utcnow()
            db.session.commit()

            # Optionally clear cart for server-side validation if you store cart server-side,
            # but don't clear client session here (webhook cannot access client session).
            try:
                send_order_status_update_email(order, old_status, 'confirmed')
            except Exception as e:
                current_app.logger.error(f"Webhook email error: {e}")

    return 'ok', 200


# ---------- CASH ON DELIVERY CONFIRM ----------
@bp.route('/checkout/cash/<int:order_id>', methods=['POST'])
@login_required
def confirm_cash_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.customer_id != current_user.id:
        flash('Unauthorized', 'danger'); return redirect(url_for('orders.my_orders'))

    order.payment_method = 'cash'
    order.status = 'confirmed'
    order.payment_status = 'pending'
    order.updated_at = datetime.utcnow()
    db.session.commit()

    # Clear cart after confirming cash order
    session.pop('cart', None)
    
    # EMAIL
    try:
        send_order_confirmation_email(order)
    except Exception as e:
        current_app.logger.error(f"Failed to send order confirmation email: {e}")

    flash('Order placed – pay cash on delivery!', 'success')
    return redirect(url_for('orders.order_confirmation', order_id=order.id))


# Other routes (order_confirmation, my_orders, track_order, cancel_order...) remain unchanged (reuse your existing ones)


# -------------- ORDER MANAGEMENT VIEW ----------
@bp.route('/order_confirmation/<int:order_id>')
@login_required
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)

    if order.customer_id != current_user.id and not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('main.index'))

    # Compute expected delivery time
    estimated_delivery = order.created_at + timedelta(minutes=30)

    return render_template(
        'order_confirmation.html',
        order=order,
        estimated_delivery=estimated_delivery
    )


@bp.route('/my_orders')
@login_required
def my_orders():
    orders = Order.query.filter_by(customer_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('my_orders.html', orders=orders)

@bp.route('/cart_count')
def cart_count():
    if 'cart' not in session:
        return {'count': 0}
    return {'count': sum(item['quantity'] for item in session['cart'].values())}


@bp.route('/track_order/<order_number>')
def track_order(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()

    # Define the order of statuses
    status_order = [
        'Pending',
        'Confirmed',
        'Preparing',
        'Out for Delivery',
        'Delivered'
    ]

    # Which step is the current status?
    current_index = status_order.index(order.status) if order.status in status_order else -1

    return render_template(
        'track_order.html',
        order=order,
        status_order=status_order,
        current_index=current_index
    )



@bp.route('/cancel_order/<int:order_id>', methods=['POST'])
@login_required
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)

    # Only owner OR admin can access
    if order.customer_id != current_user.id and not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('main.index'))

    # If USER (not admin) tries to cancel a PAID order → block it
    if not current_user.is_admin and order.payment_status == 'paid':
        flash('You cannot cancel a paid order. Please contact support.', 'danger')
        return redirect(url_for('orders.my_orders'))

    # Order must be in a cancellable state
    if order.status not in ['pending', 'confirmed']:
        flash('This order cannot be cancelled', 'warning')
        return redirect(url_for('orders.my_orders'))

    old_status = order.status
    order.status = 'cancelled'
    order.updated_at = datetime.utcnow()

    db.session.commit()

    # Send status update email
    try:
        send_order_status_update_email(order, old_status, 'cancelled')
    except Exception as e:
        current_app.logger.error(f"Failed to send order cancellation email: {e}")

    flash('Order cancelled successfully', 'success')
    return redirect(url_for('orders.my_orders' if not current_user.is_admin else 'admin.orders'))



@bp.route('/update_order_status/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    old_status = order.status

    order.status = new_status
    order.updated_at = datetime.utcnow()
    db.session.commit()

    # Send status update email
    try:
        send_order_status_update_email(order, old_status, new_status)
    except Exception as e:
        current_app.logger.error(f"Failed to send order status update email: {e}")

    flash(f'Order {order.order_number} status updated to {new_status}', 'success')
    return redirect(url_for('admin.orders'))