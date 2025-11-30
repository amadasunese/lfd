from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from sqlalchemy import event

from sqlalchemy.dialects.postgresql import JSON

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    orders = db.relationship('Order', backref='customer', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(200))
    
    items = db.relationship('MenuItem', backref='category', lazy='dynamic')
    
    def __repr__(self):
        return f'<Category {self.name}>'

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(200))
    is_available = db.Column(db.Boolean, default=True)
    preparation_time = db.Column(db.Integer, default=15)  # in minutes
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    order_items = db.relationship('OrderItem', backref='menu_item', lazy='dynamic')
    
    def __repr__(self):
        return f'<MenuItem {self.name}>'



class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subtotal_amount = db.Column(db.Float, default=0.0)
    discount_amount = db.Column(db.Float, default=0.0)
    coupon_id = db.Column(db.Integer, db.ForeignKey('coupon.id'), nullable=True)

    delivery_zone_id = db.Column(db.Integer, db.ForeignKey('delivery_zone.id'), nullable=True)
    delivery_fee = db.Column(db.Float, default=0.0)
    
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(20), default='pending')
    payment_method = db.Column(db.String(50))
    delivery_address = db.Column(db.Text)
    phone_number = db.Column(db.String(20))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    paystack_ref   = db.Column(db.String(40), unique=True, nullable=True)
    payment_status = db.Column(db.String(20), default='pending')
    
    order_items = db.relationship('OrderItem', backref='order', lazy='dynamic', cascade='all, delete-orphan')
    # Relationship — FIX
    delivery_zone = db.relationship("DeliveryZone", backref="orders", lazy=True)
    
    
    def generate_order_number(self):
        """Generate order number based on current date and order ID"""
        date_str = datetime.utcnow().strftime('%Y%m%d')
        return f"LFD{date_str}{self.id:04d}"

@event.listens_for(Order, 'after_insert')
def receive_after_insert(mapper, connection, target):
    """Automatically set order number after insert"""
    order_table = Order.__table__
    connection.execute(
        order_table.update().
        where(order_table.c.id == target.id).
        values(order_number=target.generate_order_number())
    )
    
class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    
    def __repr__(self):
        return f'<OrderItem {self.id}>'
    
    

class DeliveryZone(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(80), nullable=False, unique=True)   # GRA, Ugbowo …
    fee         = db.Column(db.Integer, nullable=False)                   # Naira
    eta         = db.Column(db.String(40), nullable=True)  # e.g., "20–30 mins"
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<DeliveryZone {self.name} – ₦{self.fee} | ETA {self.eta}>'


coupon_zone = db.Table('coupon_zone',
    db.Column('coupon_id', db.Integer, db.ForeignKey('coupon.id')),
    db.Column('zone_id', db.Integer, db.ForeignKey('delivery_zone.id'))
)

class Coupon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), nullable=False, unique=True, index=True)
    coupon_type = db.Column(db.String(10), nullable=False, default='percent')  # 'percent' or 'fixed'
    amount = db.Column(db.Float, nullable=False, default=0.0)  # percent as 10.0 for 10% or fixed currency
    starts_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    min_subtotal = db.Column(db.Float, nullable=True)   # min order subtotal to apply coupon
    max_uses = db.Column(db.Integer, nullable=True)     # global uses allowed, None => unlimited
    max_uses_per_user = db.Column(db.Integer, nullable=True)  # per-user uses allowed
    uses_count = db.Column(db.Integer, default=0)       # total times used
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # optional admin id
    note = db.Column(db.String(255), nullable=True)
    zones = db.relationship('DeliveryZone', secondary=coupon_zone, backref='coupons')

    def is_valid_now(self):
        now = datetime.utcnow()
        if not self.is_active:
            return False
        if self.starts_at and now < self.starts_at:
            return False
        if self.expires_at and now > self.expires_at:
            return False
        if self.max_uses is not None and self.uses_count >= self.max_uses:
            return False
        return True



class CouponUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    coupon_id = db.Column(db.Integer, db.ForeignKey('coupon.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=True)
    used_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    
# class DeliveryArea(db.Model):
#     __tablename__ = 'delivery_areas'
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(120), nullable=False, unique=True)   # e.g., "GRA"
#     base_fee = db.Column(db.Numeric(10,2), nullable=False, default=0.0)
#     per_km_fee = db.Column(db.Numeric(10,2), nullable=False, default=0.0)  # optional distance component
#     active = db.Column(db.Boolean, default=True)
#     description = db.Column(db.Text)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

#     def as_dict(self):
#         return {
#             'id': self.id,
#             'name': self.name,
#             'base_fee': float(self.base_fee),
#             'per_km_fee': float(self.per_km_fee),
#             'active': self.active,
#             'description': self.description
#         }

# class DeliveryZone(db.Model):
#     __tablename__ = 'delivery_zones'
#     id = db.Column(db.Integer, primary_key=True)
#     title = db.Column(db.String(120), nullable=False)
#     # store polygon as GeoJSON feature/geometry
#     polygon = db.Column(JSON, nullable=False)   # Example: GeoJSON geometry object
#     delivery_area_id = db.Column(db.Integer, db.ForeignKey('delivery_areas.id'), nullable=True)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

#     delivery_area = db.relationship('DeliveryArea', backref='zones')
