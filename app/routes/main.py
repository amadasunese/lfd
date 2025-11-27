# from flask import Blueprint, render_template, request, flash, redirect, url_for
# from flask_login import login_required, current_user
# from app.models import MenuItem, Category, Order
# from app import db

# bp = Blueprint('main', __name__)

# @bp.route('/')
# def index():
#     featured_items = MenuItem.query.filter_by(is_available=True).limit(6).all()
#     categories = Category.query.all()
#     return render_template('index.html', featured_items=featured_items, categories=categories)

# @bp.route('/about')
# def about():
#     return render_template('about.html')

# @bp.route('/contact', methods=['GET', 'POST'])
# def contact():
#     if request.method == 'POST':
#         name = request.form.get('name')
#         email = request.form.get('email')
#         message = request.form.get('message')
#         # Here you would typically send an email or save to database
#         flash('Thank you for your message! We will get back to you soon.', 'success')
#         return redirect(url_for('main.contact'))
#     return render_template('contact.html')






from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import MenuItem, Category, Order
from app import db

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    featured_items = MenuItem.query.filter_by(is_available=True).limit(6).all()
    categories = Category.query.all()
    return render_template('index.html', featured_items=featured_items, categories=categories)

@bp.route('/about')
def about():
    return render_template('about.html')

@bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        # Here you would typically send an email or save to database
        flash('Thank you for your message! We will get back to you soon.', 'success')
        return redirect(url_for('main.contact'))
    return render_template('contact.html')

@bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@bp.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    current_user.first_name = request.form.get('first_name')
    current_user.last_name = request.form.get('last_name')
    current_user.email = request.form.get('email')
    current_user.phone = request.form.get('phone')
    current_user.address = request.form.get('address')
    
    db.session.commit()
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('main.profile'))