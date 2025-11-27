import time
from flask import Blueprint, render_template, request, flash, redirect, url_for, session, current_app
from flask_login import login_required, current_user
from app.models import Order, OrderItem, MenuItem
from app.models import db
from datetime import datetime, timedelta
from app.utils.email import send_order_confirmation_email, send_order_status_update_email
from app.utils.paystack import init_payment, paystack
import hmac, hashlib
from paystackapi.transaction import Transaction

bp = Blueprint('orders', __name__)

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

    # Here you would typically use a session or database to store cart items
    # For simplicity, we'll use a basic implementation
    if 'cart' not in session:
        session['cart'] = {}

    cart = session['cart']
    if str(item_id) in cart:
        cart[str(item_id)]['quantity'] += quantity
    else:
        cart[str(item_id)] = {
            'name': item.name,
            'price': item.price,
            'quantity': quantity
        }

    session['cart'] = cart

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
        session['cart'] = session['cart']  # Trigger session update

    flash('Item removed from cart!', 'success')
    return redirect(url_for('orders.cart'))


@bp.route('/checkout', methods=['GET'])
@login_required
def checkout():
    # Render the delivery form (if order_id provided, lookup the order to show payment)
    order = None
    order_id = request.args.get('order_id', type=int)
    if order_id:
        order = Order.query.get(order_id)
        if order and order.customer_id != current_user.id and not current_user.is_admin:
            flash('Access denied', 'danger')
            return redirect(url_for('main.index'))

    return render_template('checkout.html', order=order)



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

    if order.customer_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('main.index'))

    if order.status not in ['pending', 'confirmed']:
        flash('This order cannot be cancelled', 'warning')
        return redirect(url_for('orders.my_orders'))

    old_status = order.status
    order.status = 'cancelled'
    db.session.commit()

    # Send status update email
    try:
        send_order_status_update_email(order, old_status, 'cancelled')
    except Exception as e:
        current_app.logger.error(f"Failed to send order status update email: {e}")

    flash('Order cancelled successfully', 'success')
    return redirect(url_for('orders.my_orders'))


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


# ---------- 1.  CREATE ORDER (runs first) ----------
@bp.route('/checkout/create', methods=['POST'])
@login_required
def create_order():
    """Create order record -> redirect to payment choice"""
    cart = session.get('cart', {})
    if not cart:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('menu.menu'))

    # compute subtotal exactly like your template
    subtotal = sum(d['quantity'] * d['price'] for d in cart.values())
    delivery_fee = 2.99
    tax = subtotal * 0.08
    total = subtotal + delivery_fee + tax

    # Create order
    order = Order(
        order_number = f"LFD{int(time.time())}",
        customer_id  = current_user.id,
        total_amount = total,
        status       = 'pending',
        payment_method = 'pending',
        delivery_address = request.form.get('delivery_address', ''),
        phone_number     = request.form.get('phone_number', ''),
        notes            = request.form.get('notes', ''),
        created_at   = datetime.utcnow(),
        updated_at   = datetime.utcnow()
    )

    db.session.add(order)
    db.session.flush()

    # generate real order number (depends on order.id or other logic)
    order.order_number = order.generate_order_number() if hasattr(order, 'generate_order_number') else f"LFD{order.id:06d}"

    # Add order items (correct order_id and menu_item_id)
    for item_id, d in cart.items():
        try:
            menu_item = MenuItem.query.get(int(item_id))
        except Exception:
            menu_item = None

        if not menu_item:
            current_app.logger.warning(f"MenuItem {item_id} missing when creating order {order.id}")
            continue

        order_item = OrderItem(
            order_id = order.id,
            menu_item_id = menu_item.id,
            quantity = d['quantity'],
            unit_price = d['price'],
            subtotal = d['quantity'] * d['price']
        )
        db.session.add(order_item)

    # commit everything
    db.session.commit()

    # Optionally send confirmation email (non-blocking ideally)
    try:
        send_order_confirmation_email(order)
    except Exception as e:
        current_app.logger.error(f"Failed to send order confirmation email: {e}")

    session.pop('cart', None)          # clear cart
    flash('Order created – choose payment method', 'info')
    return redirect(url_for('orders.checkout', order_id=order.id))



# ---------- 2.  PAYSTACK REDIRECT ----------
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

    # Handle both dict and string responses
    if isinstance(result, dict):
        checkout_url = result.get('authorization_url') or result.get('url')
        reference = result.get('reference') or result.get('ref')
    else:
        checkout_url = result   # treat as URL string
        reference = None

    # Save reference if available
    if reference:
        order.paystack_ref = reference
        db.session.commit()

    # Redirect user to Paystack checkout page
    if checkout_url:
        return redirect(checkout_url)

    flash('Gateway error – try again', 'warning')
    return redirect(url_for('orders.checkout', order_id=order.id))



# ---------- 3.  PAYSTACK RETURN URL ----------
# @bp.route('/pay/callback')
# @login_required
# def paystack_callback():
#     ref = request.args.get('reference')
#     if not ref:
#         flash('No reference returned', 'warning')
#         return redirect(url_for('orders.my_orders'))

#     resp = paystack.verify_transaction(ref)

#     if resp['status'] and resp['data']['status'] == 'success':
#         order = Order.query.filter_by(paystack_ref=ref).first_or_404()
#         order.status = 'confirmed'
#         db.session.commit()

#         # ✅ Clear cart HERE after confirming payment with Paystack
#         session.pop('cart', None)

#         flash('Payment successful! Your order is confirmed.', 'success')
#         return redirect(url_for('orders.order_confirmation', order_id=order.id))

#     flash('Payment failed or cancelled', 'warning')
#     return redirect(url_for('orders.my_orders'))

@bp.route('/pay/callback')
@login_required
def paystack_callback():
    ref = request.args.get('reference')
    if not ref:
        flash('No reference returned', 'warning')
        return redirect(url_for('orders.my_orders'))

    # ✅ Use Transaction.verify instead of paystack.verify_transaction
    resp = Transaction.verify(reference=ref)

    if resp['status'] and resp['data']['status'] == 'success':
        order = Order.query.filter_by(paystack_ref=ref).first_or_404()
        order.status = 'confirmed'
        db.session.commit()

        # Clear cart after confirming payment
        session.pop('cart', None)

        flash('Payment successful! Your order is confirmed.', 'success')
        return redirect(url_for('orders.order_confirmation', order_id=order.id))

    flash('Payment failed or cancelled', 'warning')
    return redirect(url_for('orders.my_orders'))


# ---------- 4.  WEBHOOK (server→server) ----------
@bp.route('/pay/webhook', methods=['POST'])
def paystack_webhook():
    sig = request.headers.get('x-paystack-signature')
    if not hmac.new(current_app.config['PAYSTACK_SECRET_KEY'].encode(),
                    request.data, hashlib.sha512).hexdigest() == sig:
        return 'bad signature', 400

    event = request.get_json(force=True)
    if event['event'] == 'charge.success':
        order = Order.query.filter_by(paystack_ref=event['data']['reference']).first()
        if order and order.payment_status == 'pending':
            order.payment_status = 'paid'
            order.status = 'confirmed'
            db.session.commit()
    return 'ok', 200

# @bp.route('/pay/webhook', methods=['POST'])
# def paystack_webhook():
#     json_input = request.get_json(force=True)
#     signature = request.headers.get('x-paystack-signature')

#     if not _valid_signature(request.data, signature):
#         return 'invalid signature', 400

#     event = json_input.get("event")
#     data = json_input.get("data", {})

#     if event == "charge.success":
#         reference = data.get("reference")
#         order = Order.query.filter_by(paystack_ref=reference).first()

#         if order and order.status == "pending":
#             order.status = "confirmed"
#             order.updated_at = datetime.utcnow()
#             db.session.commit()

#             # ✅ CLEAR CART ONLY NOW (successful payment)
#             session.pop("cart", None)

#     return "ok", 200


@bp.route('/checkout/cash/<int:order_id>', methods=['POST'])
@login_required
def confirm_cash_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.customer_id != current_user.id:
        flash('Unauthorized', 'danger'); return redirect(url_for('orders.my_orders'))
    order.payment_method = 'cash'
    order.status = 'confirmed'          # still accepted
    db.session.commit()
    flash('Order placed – pay cash on delivery!', 'success')
    return redirect(url_for('orders.order_confirmation', order_id=order.id))