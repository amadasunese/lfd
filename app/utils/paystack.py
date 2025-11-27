from flask import url_for
from paystackapi.paystack import Paystack
from paystackapi.transaction import Transaction
import uuid, os
from app.models import db

paystack = Paystack(secret_key=os.getenv('PAYSTACK_SECRET_KEY'))

def init_payment(order, user):
    """Call Paystack initialise API -> return checkout URL"""
    ref = str(uuid.uuid4())                 # unique for this payment
    amount_kobo = int(order.total_amount * 100)  # Paystack wants kobo
    resp = Transaction.initialize(
        reference=ref,
        amount=amount_kobo,
        email=user.email,
        callback_url=url_for('orders.paystack_callback', _external=True),
        metadata={'order_id': order.id}     # we’ll need this in webhook
    )
    if resp['status']:
        order.paystack_ref = ref            # save so we can verify later
        db.session.commit()
        return resp['data']['authorization_url']
    return None