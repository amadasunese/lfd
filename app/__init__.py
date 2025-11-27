from dotenv import load_dotenv
import os
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config
from flask_mail import Mail


db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
mail = Mail()     # <-- ADD THIS

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    from app.models import User

    # 🔥 REQUIRED: Load user from session
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.routes.main import bp as main_bp
    from app.routes.auth import bp as auth_bp
    from app.routes.menu import bp as menu_bp
    from app.routes.orders import bp as orders_bp
    from app.routes.admin import bp as admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(menu_bp, url_prefix='/menu')
    app.register_blueprint(orders_bp, url_prefix='/orders')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    @app.context_processor
    def cart_context():
        cart = session.get('cart', {})
        # quantity-sum version → total = sum(d['quantity'] for d in cart.values())
        total_items = len(cart)                      # distinct items
        in_cart_ids   = {int(k) for k in cart.keys()}
        return dict(total_items=total_items, in_cart_ids=in_cart_ids)


    # @app.template_filter('menu_image')
    # def menu_image_filter(image_url, item_name):
    #     """Filter to handle menu item images with fallback"""
    #     if image_url and image_url != 'None' and image_url != '':
    #         # Check if it's already a complete URL
    #         if image_url.startswith(('http://', 'https://', '/static/')):
    #             return image_url
    #         else:
    #             # Assume it's a relative path from static folder
    #             return f'/static/images/menu{image_url}'
    #     else:
    #         # Return placeholder with first letter
    #         return f"https://via.placeholder.com/50x50?text={item_name[0].upper()}"


    # # In your main app file or utilities
    # def get_menu_image_path(item_name, image_url=None):
    #     """Helper function to get the correct menu item image path"""
    #     if image_url and image_url != 'None':
    #         return image_url

    #     # Convert item name to filename format
    #     # e.g., "Spring Rolls" -> "spring-rolls.jpg"
    #     filename = item_name.lower().replace(' ', '-').replace(',', '') + '.jpg'
    #     return f'images/menu/{filename}'

    # # Register as template filter
    # @app.template_filter('menu_image_path')
    # def menu_image_path_filter(item_name, image_url=None):
    #     return get_menu_image_path(item_name, image_url)


    # Create tables
    with app.app_context():
        db.create_all()

    return app
