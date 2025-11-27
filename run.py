import os
import requests
from app import create_app, db
from app.models import User, Category, MenuItem

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Category': Category, 'MenuItem': MenuItem}

@app.cli.command()
def init_db():
    """Initialize the database."""
    db.create_all()
    print('Database initialized.')

@app.cli.command()
def create_admin():
    """Create admin user."""
    username = input('Enter admin username: ')
    email = input('Enter admin email: ')
    password = input('Enter admin password: ')
    
    admin = User(
        username=username,
        email=email,
        first_name='Admin',
        last_name='User',
        is_admin=True
    )
    admin.set_password(password)
    
    db.session.add(admin)
    db.session.commit()
    print(f'Admin user {username} created successfully.')

# @app.cli.command()
# def seed_data():
#     """Seed database with sample data."""
#     # Create categories
#     categories = [
#         Category(name='Appetizers', description='Start your meal right'),
#         Category(name='Main Courses', description='Hearty and delicious main dishes'),
#         Category(name='Desserts', description='Sweet endings'),
#         Category(name='Beverages', description='Refreshing drinks')
#     ]
    
#     for category in categories:
#         db.session.add(category)
#     db.session.commit()
    
#     # Create menu items
#     menu_items = [
#         # Appetizers
#         MenuItem(name='Spring Rolls', description='Crispy vegetable spring rolls with sweet chili sauce', price=6.99, category_id=1, preparation_time=10),
#         MenuItem(name='Caesar Salad', description='Fresh romaine lettuce with Caesar dressing and parmesan', price=8.99, category_id=1, preparation_time=5),
        
#         # Main Courses
#         MenuItem(name='Grilled Salmon', description='Perfectly grilled salmon with lemon butter sauce', price=24.99, category_id=2, preparation_time=20),
#         MenuItem(name='Chicken Parmesan', description='Breaded chicken breast with marinara sauce and mozzarella', price=18.99, category_id=2, preparation_time=25),
#         MenuItem(name='Beef Tenderloin', description='Tender beef tenderloin with red wine reduction', price=32.99, category_id=2, preparation_time=30),
        
#         # Desserts
#         MenuItem(name='Chocolate Lava Cake', description='Warm chocolate cake with molten center', price=7.99, category_id=3, preparation_time=15),
#         MenuItem(name='Tiramisu', description='Classic Italian dessert with coffee and mascarpone', price=6.99, category_id=3, preparation_time=5),
        
#         # Beverages
#         MenuItem(name='Fresh Lemonade', description='Homemade lemonade with fresh mint', price=3.99, category_id=4, preparation_time=2),
#         MenuItem(name='Iced Coffee', description='Cold brew coffee with cream and sugar', price=4.99, category_id=4, preparation_time=2)
#     ]
    
#     for item in menu_items:
#         db.session.add(item)
#     db.session.commit()
    
#     print('Sample data seeded successfully.')

@app.cli.command()
def seed_data():
    """Seed database with sample data including images."""
    # Create upload directory
    upload_dir = os.path.join(app.root_path, 'static', 'uploads', 'menu_items')
    os.makedirs(upload_dir, exist_ok=True)
    
    # Create categories
    categories = [
        Category(name='Appetizers', description='Start your meal right'),
        Category(name='Main Courses', description='Hearty and delicious main dishes'),
        Category(name='Desserts', description='Sweet endings'),
        Category(name='Beverages', description='Refreshing drinks'),
        Category(name='Salads', description='Fresh and healthy'),
        Category(name='Pizza', description='Stone-baked pizzas')
    ]
    
    for category in categories:
        db.session.add(category)
    db.session.commit()
    
    # Image URLs for different food categories (from Unsplash)
    image_urls = {
        'appetizers': [
            'https://images.unsplash.com/photo-1541014741259-de529411b96a?w=400',
            'https://images.unsplash.com/photo-1559847844-d724b851b7d2?w=400',
            'https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=400'
        ],
        'main_courses': [
            'https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=400',
            'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=400',
            'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400',
            'https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=400'
        ],
        'desserts': [
            'https://images.unsplash.com/photo-1565958011703-44f9829ba187?w=400',
            'https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=400',
            'https://images.unsplash.com/photo-1551024506-0bccd828d307?w=400'
        ],
        'beverages': [
            'https://images.unsplash.com/photo-1544145945-f90425340c7e?w=400',
            'https://images.unsplash.com/photo-1551538827-9c037cb4f32a?w=400',
            'https://images.unsplash.com/photo-1505252585461-14db1eb44964?w=400'
        ],
        'salads': [
            'https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=400',
            'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=400',
            'https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=400'
        ],
        'pizza': [
            'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=400',
            'https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=400',
            'https://images.unsplash.com/photo-1565299507177-b0ac66763828?w=400'
        ]
    }
    
    # Menu items with images
    menu_items = [
        # Appetizers
        {
            'name': 'Spring Rolls', 'description': 'Crispy vegetable spring rolls with sweet chili sauce',
            'price': 6.99, 'category_id': 1, 'preparation_time': 10,
            'image_url': image_urls['appetizers'][0]
        },
        {
            'name': 'Caesar Salad', 'description': 'Fresh romaine lettuce with Caesar dressing and parmesan',
            'price': 8.99, 'category_id': 1, 'preparation_time': 5,
            'image_url': image_urls['appetizers'][1]
        },
        {
            'name': 'Bruschetta', 'description': 'Grilled bread with tomatoes, garlic, and basil',
            'price': 7.99, 'category_id': 1, 'preparation_time': 8,
            'image_url': image_urls['appetizers'][2]
        },
        
        # Main Courses
        {
            'name': 'Grilled Salmon', 'description': 'Perfectly grilled salmon with lemon butter sauce',
            'price': 24.99, 'category_id': 2, 'preparation_time': 20,
            'image_url': image_urls['main_courses'][0]
        },
        {
            'name': 'Chicken Parmesan', 'description': 'Breaded chicken breast with marinara sauce and mozzarella',
            'price': 18.99, 'category_id': 2, 'preparation_time': 25,
            'image_url': image_urls['main_courses'][1]
        },
        {
            'name': 'Beef Tenderloin', 'description': 'Tender beef tenderloin with red wine reduction',
            'price': 32.99, 'category_id': 2, 'preparation_time': 30,
            'image_url': image_urls['main_courses'][2]
        },
        {
            'name': 'Vegetable Pasta', 'description': 'Fresh pasta with seasonal vegetables in garlic olive oil',
            'price': 16.99, 'category_id': 2, 'preparation_time': 15,
            'image_url': image_urls['main_courses'][3]
        },
        
        # Desserts
        {
            'name': 'Chocolate Lava Cake', 'description': 'Warm chocolate cake with molten center',
            'price': 7.99, 'category_id': 3, 'preparation_time': 15,
            'image_url': image_urls['desserts'][0]
        },
        {
            'name': 'Tiramisu', 'description': 'Classic Italian dessert with coffee and mascarpone',
            'price': 6.99, 'category_id': 3, 'preparation_time': 5,
            'image_url': image_urls['desserts'][1]
        },
        {
            'name': 'Cheesecake', 'description': 'Creamy New York style cheesecake with berry compote',
            'price': 8.99, 'category_id': 3, 'preparation_time': 5,
            'image_url': image_urls['desserts'][2]
        },
        
        # Beverages
        {
            'name': 'Fresh Lemonade', 'description': 'Homemade lemonade with fresh mint',
            'price': 3.99, 'category_id': 4, 'preparation_time': 2,
            'image_url': image_urls['beverages'][0]
        },
        {
            'name': 'Iced Coffee', 'description': 'Cold brew coffee with cream and sugar',
            'price': 4.99, 'category_id': 4, 'preparation_time': 2,
            'image_url': image_urls['beverages'][1]
        },
        {
            'name': 'Fresh Orange Juice', 'description': 'Freshly squeezed orange juice',
            'price': 5.99, 'category_id': 4, 'preparation_time': 3,
            'image_url': image_urls['beverages'][2]
        },
        
        # Salads
        {
            'name': 'Greek Salad', 'description': 'Fresh vegetables with feta cheese and olives',
            'price': 12.99, 'category_id': 5, 'preparation_time': 8,
            'image_url': image_urls['salads'][0]
        },
        {
            'name': 'Quinoa Bowl', 'description': 'Healthy quinoa with roasted vegetables',
            'price': 14.99, 'category_id': 5, 'preparation_time': 12,
            'image_url': image_urls['salads'][1]
        },
        
        # Pizza
        {
            'name': 'Margherita Pizza', 'description': 'Classic pizza with tomato, mozzarella, and basil',
            'price': 18.99, 'category_id': 6, 'preparation_time': 20,
            'image_url': image_urls['pizza'][0]
        },
        {
            'name': 'Pepperoni Pizza', 'description': 'Pizza with pepperoni and cheese',
            'price': 21.99, 'category_id': 6, 'preparation_time': 20,
            'image_url': image_urls['pizza'][1]
        },
        {
            'name': 'Vegetarian Pizza', 'description': 'Pizza with assorted vegetables',
            'price': 19.99, 'category_id': 6, 'preparation_time': 20,
            'image_url': image_urls['pizza'][2]
        }
    ]
    
    # Create menu items
    for item_data in menu_items:
        item = MenuItem(**item_data)
        db.session.add(item)
    
    db.session.commit()
    
    # Download and save images locally (optional)
    print("Downloading images...")
    for i, item_data in enumerate(menu_items):
        if 'image_url' in item_data:
            try:
                response = requests.get(item_data['image_url'], timeout=10)

                if response.status_code == 200:
                    # Save image with proper filename
                    filename = f"menu_item_{i+1}.jpg"
                    filepath = os.path.join(upload_dir, filename)
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    
                    # Update the database with local path
                    item = MenuItem.query.filter_by(name=item_data['name']).first()
                    if item:
                        item.image_url = f"static/uploads/menu_items/{filename}"
                        db.session.commit()
                    print(f"Downloaded: {filename}")
                else:
                    print(f"Failed to download image for {item_data['name']}")
            except Exception as e:
                print(f"Error downloading image for {item_data['name']}: {e}")
    
    print('Sample data seeded successfully with images!')

@app.cli.command()
def seed_with_local_images():
    """Seed data and download images locally."""
    seed_data()

if __name__ == '__main__':
    app.run(debug=True)