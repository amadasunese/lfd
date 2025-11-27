from flask import Blueprint, render_template, request, jsonify, flash
from app.models import MenuItem, Category
from app import db

bp = Blueprint('menu', __name__)

@bp.route('/')
def menu():
    category_id = request.args.get('category')
    search_query = request.args.get('search')
    
    query = MenuItem.query.filter_by(is_available=True)
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if search_query:
        query = query.filter(MenuItem.name.contains(search_query))
    
    items = query.all()
    categories = Category.query.all()
    
    return render_template('menu.html', items=items, categories=categories)

@bp.route('/item/<int:item_id>')
def item_detail(item_id):
    item = MenuItem.query.get_or_404(item_id)
    return render_template('item_detail.html', item=item)