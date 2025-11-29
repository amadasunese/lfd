import os
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from flask import current_app, render_template_string
from dotenv import load_dotenv
load_dotenv()

# Gmail SMTP config
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_PASS")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
SMTP_DEBUG = int(os.getenv("SMTP_DEBUG", 0))


def send_email(to, subject, body, is_html=False):
    """
    Sends an email via Gmail SMTP.
    Can send plain text or HTML formatted messages.
    """
    msg = MIMEMultipart()
    msg["From"] = GMAIL_USER
    msg["To"] = to
    msg["Subject"] = subject

    mime_type = "html" if is_html else "plain"
    msg.attach(MIMEText(body, mime_type))

    print("📧 Using Gmail user:", GMAIL_USER)
    print("🔑 Using Gmail pass:", "None" if not GMAIL_PASS else "*" * len(GMAIL_PASS))

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.set_debuglevel(SMTP_DEBUG)
            server.login(GMAIL_USER, GMAIL_PASS)
            server.send_message(msg)

        return True, "✅ Email sent successfully."

    except Exception as e:
        error_trace = traceback.format_exc()
        error_message = f"❌ SMTP Error: {str(e)}\n{error_trace}"
        print(error_message)
        return False, str(e)


def send_order_confirmation_email(order):
    subject = f'Order Confirmation - {order.order_number}'
    recipients = [order.customer.email]

    text_body = f'''
Dear {order.customer.first_name},

Thank you for your order at Lauracious Foodies Delight!

Order Number: {order.order_number}
Total Amount: ₦{order.total_amount:.2f}
Status: {order.status.title()}

We are preparing your order with love and it will be delivered to:
{order.delivery_address}

Estimated delivery time: 30-45 minutes

You can track your order status using your order number.

Best regards,
The Lauracious Foodies Delight Team
'''

    html_body = render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #ff6b6b, #4ecdc4); color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }
        .order-details { background: white; padding: 20px; border-radius: 10px; margin: 20px 0; }
        .footer { text-align: center; margin-top: 30px; color: #666; }
        .btn { display: inline-block; padding: 12px 24px; background: #ff6b6b; color: white; text-decoration: none; border-radius: 25px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Order Confirmation</h1>
        </div>
        <div class="content">
            <h2>Hello {{ order.customer.first_name }}!</h2>
            <p>Thank you for your order at <strong>Lauracious Foodies Delight</strong>!</p>

            <div class="order-details">
                <h3>Order Details</h3>
                <p><strong>Order Number:</strong> {{ order.order_number }}</p>
                <p><strong>Total Amount:</strong> ₦{{ "%.2f"|format(order.total_amount) }}</p>
                <p><strong>Status:</strong> {{ order.status.title() }}</p>
                <p><strong>Delivery Address:</strong><br>{{ order.delivery_address }}</p>

                <h4>Items Ordered:</h4>
                <ul>
                {% for order_item in order.order_items %}
                    <li>{{ order_item.quantity }}x {{ order_item.menu_item.name }} - ₦{{ "%.2f"|format(order_item.subtotal) }}</li>
                {% endfor %}
                </ul>
            </div>

            <p><strong>Estimated delivery time:</strong> 30-45 minutes</p>
            <p>We are preparing your order with love and care!</p>

            <div class="footer">
                <p>Best regards,<br>The Lauracious Foodies Delight Team</p>
                <p><small>If you have any questions, please contact us at hello@lauraciousfoodies.com</small></p>
            </div>
        </div>
    </div>
</body>
</html>
    ''', order=order)

    # Send email via Gmail SMTP
    send_email(recipients[0], subject, html_body, is_html=True)



def send_order_status_update_email(order, old_status, new_status):
    subject = f'Order Status Update - {order.order_number}'
    recipient = order.customer.email

    html_body = render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #4ecdc4, #44a08d); color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }
        .status-update { background: white; padding: 20px; border-radius: 10px; margin: 20px 0; text-align: center; }
        .footer { text-align: center; margin-top: 30px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Order Status Update</h1>
        </div>
        <div class="content">
            <h2>Hello {{ order.customer.first_name }}!</h2>
            <p>Your order status has been updated!</p>

            <div class="status-update">
                <h3>Order #{{ order.order_number }}</h3>
                <p><strong>Previous Status:</strong> {{ old_status.title() }}</p>
                <p><strong>New Status:</strong> {{ new_status.title() }}</p>
            </div>

            <div class="footer">
                <p>Thank you for choosing <strong>Lauracious Foodies Delight</strong>!</p>
                <p>Best regards,<br>The Lauracious Foodies Delight Team</p>
            </div>
        </div>
    </div>
</body>
</html>
    ''', order=order, old_status=old_status, new_status=new_status)

    try:
        # send_email(to, subject, body, is_html)
        success, _ = send_email(recipient, subject, html_body, is_html=True)
        return success
    except Exception as e:
        current_app.logger.exception(f"Failed to send order status email: {e}")
        return False