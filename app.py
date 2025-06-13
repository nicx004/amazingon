import sqlite3
from flask import Flask, render_template, request, redirect, session, flash, url_for # type: ignore

app = Flask(__name__, template_folder="templates")
app.secret_key = 'theultimatesecretkey'

def get_db_connection():
    conn = sqlite3.connect('database2.db')
    conn.row_factory = sqlite3.Row
    return conn

# Home page (Browse Products)
@app.route('/')
def index():
    conn = get_db_connection()

    categories = conn.execute('SELECT * FROM product_category').fetchall()
    products_by_category = {}

    for category in categories:
        products_by_category[category['id']] = conn.execute(
            'SELECT * FROM product WHERE category_id = ?',
            (category['id'],)
        ).fetchall()

    conn.close()

    return render_template('index.html', categories=categories, products_by_category=products_by_category)

# Add to cart
@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'user_id' not in session:
        flash("Please log in to add items to cart.", "warning")
        return redirect(url_for('login'))

    quantity = int(request.form['quantity'])
    user_id = session['user_id']

    conn = get_db_connection()

    # Check if the product is already in the cart
    existing = conn.execute('SELECT * FROM cart WHERE user_id = ? AND product_id = ?',
                            (user_id, product_id)).fetchone()

    if existing:
        new_qty = existing['quantity'] + quantity
        conn.execute('UPDATE cart SET quantity = ? WHERE id = ?', (new_qty, existing['id']))
    else:
        conn.execute('INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)',
                     (user_id, product_id, quantity))

    conn.commit()
    conn.close()

    flash("Item added to cart!", "success")
    return redirect(url_for('index'))


@app.route('/product/<int:product_id>/review', methods=['GET', 'POST'])
def review_product(product_id):
    if 'user_id' not in session:
        flash("Please log in to leave a review.", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        rating = int(request.form['rating'])
        comment = request.form['comment']
        user_id = session['user_id']

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO reviews (user_id, product_id, rating, comment) VALUES (?, ?, ?, ?)',
            (user_id, product_id, rating, comment)
        )
        conn.commit()
        conn.close()

        flash("Review submitted successfully!", "success")
        return redirect(url_for('product_detail', product_id=product_id))

    return render_template('review_form.html', product_id=product_id)


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    conn = get_db_connection()

    product = conn.execute('SELECT * FROM product WHERE id = ?', (product_id,)).fetchone()
    reviews = conn.execute("""
        SELECT r.rating, r.comment, r.created_at, u.name
        FROM reviews r
        JOIN user u ON r.user_id = u.id
        WHERE r.product_id = ?
        ORDER BY r.created_at DESC
    """, (product_id,)).fetchall()

    conn.close()

    if not product:
        return "Product not found", 404

    return render_template('product_detail.html', product=product, reviews=reviews)


# View cart
@app.route('/view_cart')
def view_cart():
    if 'user_id' not in session:
        flash("Please log in to view your cart.", "warning")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cart_items = conn.execute("""
        SELECT cart.id, product.name, product.price, cart.quantity,
               (product.price * cart.quantity) AS total
        FROM cart
        JOIN product ON cart.product_id = product.id
        WHERE cart.user_id = ?
    """, (session['user_id'],)).fetchall()

    total_amount = sum(item['total'] for item in cart_items)
    conn.close()

    return render_template('cart.html', cart_items=cart_items, total=total_amount)

# Remove from cart
@app.route('/remove_from_cart/<int:cart_id>', methods=['POST'])
def remove_from_cart(cart_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute('DELETE FROM cart WHERE id = ? AND user_id = ?', (cart_id, session['user_id']))
    conn.commit()
    conn.close()

    flash("Item removed from cart.", "info")
    return redirect(url_for('view_cart'))

# Place an order
@app.route('/place_order', methods=['POST'])
def place_order():
    if 'user_id' not in session:
        flash("Please log in to place an order.", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()

    cart_items = conn.execute("""
        SELECT product_id, quantity, product.price
        FROM cart
        JOIN product ON cart.product_id = product.id
        WHERE cart.user_id = ?
    """, (user_id,)).fetchall()

    if not cart_items:
        flash("Your cart is empty!", "danger")
        conn.close()
        return redirect(url_for('view_cart'))

    total_amount = sum(item['quantity'] * item['price'] for item in cart_items)

    # payment details
    payment_method = request.form.get('payment_method')
    card_number = request.form.get('card_number')  # ignore
    expiry_date = request.form.get('expiry_date')  # ignore
    cvv = request.form.get('cvv')  # ignore

    # Insert into order table
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO "order" (user_id, total_amount, payment_status)
        VALUES (?, ?, ?)
    """, (user_id, total_amount, 'Paid'))  # Simulating payment as "Paid"
    order_id = cursor.lastrowid

    for item in cart_items:
        cursor.execute("""
            INSERT INTO order_details (order_id, product_id, quantity, price)
            VALUES (?, ?, ?, ?)
        """, (order_id, item['product_id'], item['quantity'], item['price']))

    # Clear cart
    cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    flash("Order placed successfully!", "success")
    return redirect(url_for('view_cart'))

# View orders
@app.route('/orders')
def view_orders():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    orders = conn.execute("""
        SELECT * FROM "order"
        WHERE user_id = ?
        ORDER BY date DESC
    """, (session['user_id'],)).fetchall()
    conn.close()

    return render_template('orders.html', orders=orders)

# Register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        address = request.form['address']
        password = request.form['password']

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO user (name, email, phone, address, password) VALUES (?, ?, ?, ?, ?)',
                         (name, email, phone, address, password))
            conn.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already exists!', 'danger')
        finally:
            conn.close()

    return render_template('register.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM user WHERE email = ? AND password = ?', (email, password)).fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials.', 'danger')

    return render_template('login.html')

# Logout route
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Home route (After login)
@app.route('/home')
def home():
    if 'user_id' in session:
        return render_template('home.html', name=session['user_name'])
    else:
        return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
