import os
import pg8000
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime
import random
import string
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Neon Database Connection - Use environment variable for production
CONNECTION_STRING = os.environ.get('DATABASE_URL', 'postgresql://neondb_owner:npg_SwYlmpi0uBc4@ep-empty-mode-adhsf63n-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require')

def get_db_connection():
    try:
        # Get connection string from environment with fallback
        database_url = os.environ.get('DATABASE_URL', CONNECTION_STRING)
        
        # Parse the connection string
        if database_url.startswith('postgresql://'):
            # Remove the postgresql:// prefix
            url_parts = database_url[13:]  # Remove 'postgresql://'
            
            # Split user:password and host:port/database
            user_pass, host_db = url_parts.split('@', 1)
            username, password = user_pass.split(':', 1)
            
            # Split host:port and database
            if '/' in host_db:
                host_port, database = host_db.split('/', 1)
            else:
                host_port = host_db
                database = 'neondb'
            
            # Split host and port
            if ':' in host_port:
                host, port = host_port.split(':', 1)
            else:
                host = host_port
                port = '5432'
            
            # Remove query parameters from database name
            if '?' in database:
                database = database.split('?')[0]
            
            print(f"🔗 Connecting to: {host}:{port}/{database}")
            
            conn = pg8000.connect(
                host=host,
                user=username,
                password=password,
                database=database,
                port=int(port),
                ssl_context=True
            )
            print("✅ Database connection successful!")
            return conn
            
    except Exception as err:
        print(f"❌ Database connection failed: {err}")
        return None

def init_db():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Create guests table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS guests (
                    id SERIAL PRIMARY KEY,
                    guest_id VARCHAR(20) UNIQUE NOT NULL,
                    guest_name VARCHAR(100) NOT NULL,
                    room_number VARCHAR(10) NOT NULL,
                    room_type VARCHAR(50) NOT NULL,
                    check_in DATE NOT NULL,
                    check_out DATE NOT NULL,
                    total_amount DECIMAL(10, 2) NOT NULL,
                    email VARCHAR(100),
                    phone VARCHAR(20),
                    status VARCHAR(20) DEFAULT 'checked_in',
                    amenities_total DECIMAL(10, 2) DEFAULT 0.00,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create rooms table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rooms (
                    id SERIAL PRIMARY KEY,
                    room_number VARCHAR(10) UNIQUE NOT NULL,
                    room_type VARCHAR(50) NOT NULL,
                    price_per_night DECIMAL(10, 2) NOT NULL,
                    amenities TEXT,
                    status VARCHAR(20) DEFAULT 'available',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create amenities_orders table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS amenities_orders (
                    id SERIAL PRIMARY KEY,
                    guest_id VARCHAR(20) NOT NULL,
                    item_name VARCHAR(100) NOT NULL,
                    item_price DECIMAL(10, 2) NOT NULL,
                    quantity INTEGER NOT NULL,
                    total_price DECIMAL(10, 2) NOT NULL,
                    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insert sample rooms if empty
            cursor.execute("SELECT COUNT(*) FROM rooms")
            if cursor.fetchone()[0] == 0:
                sample_rooms = [
                    ('101', 'Standard Room', 2500.00, 'WiFi, TV, AC, King Bed'),
                    ('102', 'Standard Room', 2500.00, 'WiFi, TV, AC, Queen Bed'),
                    ('103', 'Standard Room', 2500.00, 'WiFi, TV, AC, Twin Beds'),
                    ('201', 'Deluxe Room', 4500.00, 'WiFi, Smart TV, AC, Mini Bar, King Bed'),
                    ('202', 'Deluxe Room', 4500.00, 'WiFi, Smart TV, AC, Mini Bar, Queen Bed'),
                    ('301', 'Executive Suite', 7500.00, 'WiFi, Smart TV, AC, Mini Bar, Jacuzzi, Living Area'),
                    ('302', 'Executive Suite', 7500.00, 'WiFi, Smart TV, AC, Mini Bar, Jacuzzi, Dining Area'),
                    ('401', 'Presidential Suite', 12000.00, 'WiFi, Smart TV, AC, Mini Bar, Jacuzzi, Private Pool'),
                ]
                for room in sample_rooms:
                    try:
                        cursor.execute(
                            "INSERT INTO rooms (room_number, room_type, price_per_night, amenities) VALUES (%s, %s, %s, %s)",
                            room
                        )
                    except Exception as e:
                        print(f"Room {room[0]} already exists: {e}")
                        continue
            
            conn.commit()
            cursor.close()
            print("✅ Database initialized successfully!")
            
        except Exception as err:
            print(f"❌ Database initialization error: {err}")
            conn.rollback()
        finally:
            conn.close()

# Initialize database on startup
try:
    init_db()
except Exception as e:
    print(f"⚠️ Database initialization warning: {e}")

def generate_guest_id():
    return 'G' + ''.join(random.choices(string.digits, k=8))

# Menu items for room amenities
MENU_ITEMS = {
    'food': [
        {'name': 'Club Sandwich', 'price': 450, 'category': 'food'},
        {'name': 'Margherita Pizza', 'price': 600, 'category': 'food'},
        {'name': 'Butter Chicken', 'price': 850, 'category': 'food'},
        {'name': 'Biryani', 'price': 750, 'category': 'food'},
        {'name': 'Pasta Alfredo', 'price': 550, 'category': 'food'},
        {'name': 'Grilled Fish', 'price': 900, 'category': 'food'},
    ],
    'beverages': [
        {'name': 'Coffee', 'price': 150, 'category': 'beverages'},
        {'name': 'Tea', 'price': 100, 'category': 'beverages'},
        {'name': 'Fresh Juice', 'price': 200, 'category': 'beverages'},
        {'name': 'Soft Drink', 'price': 120, 'category': 'beverages'},
        {'name': 'Mineral Water', 'price': 80, 'category': 'beverages'},
    ],
    'services': [
        {'name': 'Laundry Service', 'price': 300, 'category': 'services'},
        {'name': 'Spa Treatment', 'price': 1500, 'category': 'services'},
        {'name': 'Room Cleaning', 'price': 200, 'category': 'services'},
        {'name': 'Airport Transfer', 'price': 1200, 'category': 'services'},
    ]
}

# Test route to check database connection
@app.route('/test')
def test_route():
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return f"✅ Database connection successful! Test query result: {result}"
        else:
            return "❌ Database connection failed - no connection object returned"
    except Exception as e:
        return f"❌ Database connection error: {str(e)}"

# Routes
@app.route('/')
def index():
    try:
        conn = get_db_connection()
        available_rooms_count = 0
        
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM rooms WHERE status = 'available'")
                available_rooms_count = cursor.fetchone()[0]
                cursor.close()
            except Exception as err:
                print(f"Error loading room count: {err}")
            finally:
                conn.close()
        
        return render_template('index.html', available_rooms=available_rooms_count)
    
    except Exception as e:
        print(f"Error in index route: {e}")
        return render_template('index.html', available_rooms=0)

@app.route('/book', methods=['GET', 'POST'])
def book():
    if request.method == 'POST':
        guest_name = request.form['guest_name']
        room_number = request.form['room_number']
        check_in = request.form['check_in']
        check_out = request.form['check_out']
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                
                # Get room details
                cursor.execute("SELECT room_type, price_per_night FROM rooms WHERE room_number = %s", (room_number,))
                room_data = cursor.fetchone()
                
                if room_data:
                    room_type, price_per_night = room_data
                    
                    # Calculate total amount
                    check_in_date = datetime.strptime(check_in, '%Y-%m-%d')
                    check_out_date = datetime.strptime(check_out, '%Y-%m-%d')
                    nights = (check_out_date - check_in_date).days
                    total_amount = price_per_night * nights
                    
                    # Generate guest ID
                    guest_id = generate_guest_id()
                    
                    # Insert guest
                    cursor.execute('''
                        INSERT INTO guests (guest_id, guest_name, room_number, room_type, check_in, check_out, total_amount, email, phone)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (guest_id, guest_name, room_number, room_type, check_in, check_out, total_amount, email, phone))
                    
                    # Update room status
                    cursor.execute("UPDATE rooms SET status = 'occupied' WHERE room_number = %s", (room_number,))
                    
                    conn.commit()
                    cursor.close()
                    
                    flash(f'Booking successful! Your Guest ID is: {guest_id}', 'success')
                    return redirect(url_for('index'))
                else:
                    flash('Room not found!', 'error')
                    
            except Exception as err:
                print(f"Error during booking: {err}")
                flash('Error during booking. Please try again.', 'error')
            finally:
                conn.close()
    
    # GET request - show available rooms
    conn = get_db_connection()
    available_rooms = []
    
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT room_number, room_type, price_per_night, amenities FROM rooms WHERE status = 'available'")
            available_rooms = cursor.fetchall()
            cursor.close()
        except Exception as err:
            print(f"Error loading rooms: {err}")
        finally:
            conn.close()
    
    return render_template('book.html', available_rooms=available_rooms)

@app.route('/guest-login', methods=['GET', 'POST'])
def guest_login():
    if request.method == 'POST':
        guest_id = request.form['guest_id']
        guest_name = request.form['guest_name']
        
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM guests WHERE guest_id = %s AND guest_name = %s AND status = 'checked_in'", 
                             (guest_id, guest_name))
                guest = cursor.fetchone()
                cursor.close()
                
                if guest:
                    session['guest_id'] = guest_id
                    session['guest_name'] = guest_name
                    session['guest_logged_in'] = True
                    return redirect(url_for('guest_dashboard'))
                else:
                    flash('Invalid Guest ID or Name, or you have already checked out.', 'error')
                    
            except Exception as err:
                print(f"Error during guest login: {err}")
                flash('Error during login. Please try again.', 'error')
            finally:
                conn.close()
    
    return render_template('guest_login.html')

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username == 'admin' and password == 'official':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials!', 'error')
    
    return render_template('admin_login.html')

@app.route('/guest')
def guest_dashboard():
    if not session.get('guest_logged_in'):
        return redirect(url_for('guest_login'))
    
    guest_id = session.get('guest_id')
    conn = get_db_connection()
    guest_info = None
    
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT guest_id, guest_name, room_number, room_type, check_in, check_out, total_amount
                FROM guests WHERE guest_id = %s
            ''', (guest_id,))
            guest_info = cursor.fetchone()
            cursor.close()
        except Exception as err:
            print(f"Error loading guest info: {err}")
        finally:
            conn.close()
    
    return render_template('guest.html', guest_info=guest_info)

@app.route('/guest/amenities', methods=['GET', 'POST'])
def guest_amenities():
    if not session.get('guest_logged_in'):
        return redirect(url_for('guest_login'))
    
    guest_id = session.get('guest_id')
    
    if request.method == 'POST':
        item_name = request.form['item_name']
        quantity = int(request.form['quantity'])
        
        # Find item price
        item_price = 0
        for category in MENU_ITEMS.values():
            for item in category:
                if item['name'] == item_name:
                    item_price = item['price']
                    break
        
        total_price = item_price * quantity
        
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                
                # Insert order
                cursor.execute('''
                    INSERT INTO amenities_orders (guest_id, item_name, item_price, quantity, total_price)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (guest_id, item_name, item_price, quantity, total_price))
                
                # Update guest's amenities total
                cursor.execute('''
                    UPDATE guests SET amenities_total = amenities_total + %s WHERE guest_id = %s
                ''', (total_price, guest_id))
                
                conn.commit()
                cursor.close()
                
                flash(f'Order placed successfully! Total: ₹{total_price}', 'success')
                
            except Exception as err:
                print(f"Error placing order: {err}")
                flash('Error placing order. Please try again.', 'error')
            finally:
                conn.close()
    
    return render_template('guest_amenities.html', menu_items=MENU_ITEMS)

@app.route('/guest/billing')
def guest_billing():
    if not session.get('guest_logged_in'):
        return redirect(url_for('guest_login'))
    
    guest_id = session.get('guest_id')
    conn = get_db_connection()
    guest_info = None
    orders = []
    billing_data = {}
    
    if conn:
        try:
            cursor = conn.cursor()
            
            # Get guest info
            cursor.execute('''
                SELECT guest_id, guest_name, room_number, room_type, check_in, check_out, 
                       total_amount, amenities_total
                FROM guests WHERE guest_id = %s
            ''', (guest_id,))
            guest_info = cursor.fetchone()
            
            # Get orders
            cursor.execute('''
                SELECT item_name, item_price, quantity, total_price, order_date
                FROM amenities_orders WHERE guest_id = %s ORDER BY order_date DESC
            ''', (guest_id,))
            orders = cursor.fetchall()
            
            cursor.close()
            
            # Calculate billing totals in Python to avoid template errors
            if guest_info:
                room_charges = float(guest_info[6]) if guest_info[6] else 0.0
                amenities_total = float(guest_info[7]) if guest_info[7] else 0.0
                subtotal = room_charges + amenities_total
                gst = subtotal * 0.18
                grand_total = subtotal + gst
                
                billing_data = {
                    'room_charges': room_charges,
                    'amenities_total': amenities_total,
                    'subtotal': subtotal,
                    'gst': gst,
                    'grand_total': grand_total
                }
            
        except Exception as err:
            print(f"Error loading billing info: {err}")
        finally:
            conn.close()
    
    return render_template('guest_billing.html', 
                         guest_info=guest_info, 
                         orders=orders,
                         billing_data=billing_data)

@app.route('/guest/pay', methods=['POST'])
def guest_pay():
    if not session.get('guest_logged_in'):
        return redirect(url_for('guest_login'))
    
    guest_id = session.get('guest_id')
    conn = get_db_connection()
    
    if conn:
        try:
            cursor = conn.cursor()
            
            # Update guest status to checked_out
            cursor.execute("UPDATE guests SET status = 'checked_out' WHERE guest_id = %s", (guest_id,))
            
            # Get room number to mark as available
            cursor.execute("SELECT room_number FROM guests WHERE guest_id = %s", (guest_id,))
            room_result = cursor.fetchone()
            
            if room_result:
                room_number = room_result[0]
                cursor.execute("UPDATE rooms SET status = 'available' WHERE room_number = %s", (room_number,))
            
            conn.commit()
            cursor.close()
            
            session.pop('guest_logged_in', None)
            session.pop('guest_id', None)
            session.pop('guest_name', None)
            
            flash('Payment successful! Thank you for staying with us.', 'success')
            return redirect(url_for('index'))
            
        except Exception as err:
            print(f"Error during payment: {err}")
            flash('Error during payment. Please try again.', 'error')
        finally:
            conn.close()
    
    return redirect(url_for('guest_billing'))

@app.route('/admin')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    return render_template('admin.html')

@app.route('/admin/rooms')
def admin_rooms():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    rooms = []
    stats = {
        'total_rooms': 0,
        'available_rooms': 0,
        'occupied_rooms': 0,
        'maintenance_rooms': 0
    }
    
    if conn:
        try:
            cursor = conn.cursor()
            
            # Get all rooms
            cursor.execute("SELECT room_number, room_type, status, price_per_night FROM rooms ORDER BY room_number")
            rooms = cursor.fetchall()
            
            # Get room statistics
            cursor.execute("SELECT COUNT(*) FROM rooms")
            stats['total_rooms'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM rooms WHERE status = 'available'")
            stats['available_rooms'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM rooms WHERE status = 'occupied'")
            stats['occupied_rooms'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM rooms WHERE status = 'maintenance'")
            stats['maintenance_rooms'] = cursor.fetchone()[0]
            
            cursor.close()
            
        except Exception as err:
            print(f"Error loading room data: {err}")
        finally:
            conn.close()
    
    return render_template('admin_rooms.html', rooms=rooms, stats=stats)

@app.route('/admin/update-room-status', methods=['POST'])
def update_room_status():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    room_number = request.form['room_number']
    new_status = request.form['status']
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE rooms SET status = %s WHERE room_number = %s", (new_status, room_number))
            conn.commit()
            cursor.close()
            flash('Room status updated successfully!', 'success')
        except Exception as err:
            print(f"Error updating room status: {err}")
            flash('Error updating room status.', 'error')
        finally:
            conn.close()
    
    return redirect(url_for('admin_rooms'))

@app.route('/admin/records')
def admin_records():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    guests = []
    
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT guest_id, guest_name, room_number, room_type, check_in, check_out, 
                       total_amount, amenities_total, status, created_at
                FROM guests ORDER BY created_at DESC
            ''')
            guests = cursor.fetchall()
            cursor.close()
        except Exception as err:
            print(f"Error loading guest records: {err}")
        finally:
            conn.close()
    
    return render_template('admin_records.html', guests=guests)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Admin logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/guest/logout')
def guest_logout():
    session.pop('guest_logged_in', None)
    session.pop('guest_id', None)
    session.pop('guest_name', None)
    flash('Guest logged out successfully!', 'success')
    return redirect(url_for('index'))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

# Vercel requirement
application = app

if __name__ == '__main__':
    print("🚀 Starting Flask application...")
    app.run(host='0.0.0.0', port=5000, debug=True)
else:
    print("🚀 Application started in production mode")
