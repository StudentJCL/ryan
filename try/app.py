from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import mysql.connector
from mysql.connector import Error
from werkzeug.utils import secure_filename
import os,json



app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for flash messages and session management

UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


    
def save_image(image_file):
    """Save the uploaded image file to the server and return the filename."""
    if image_file and allowed_file(image_file.filename):
        filename = secure_filename(image_file.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(image_path)
        return filename
    return None

def allowed_file(filename):
    """Check if the uploaded file is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
# MySQL Database connection
def get_db_connection():
    conn = mysql.connector.connect(
        host='localhost',  # Your MySQL host, default is 'localhost'
        user='root',  # Your MySQL username
        password='',  # Your MySQL password
        database='ecomdb'  # The database you want to connect to
    )
    return conn
def get_product_by_id(product_id):
    """Fetch a product from the database by its ID."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT * FROM products WHERE id = %s', (product_id,))
    product = cursor.fetchone()

    cursor.close()
    conn.close()

    return product
# Route to display the homepage
@app.route('/')
def homepage():
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT * FROM products WHERE seller_id IS NOT NULL')
    seller_products = cursor.fetchall()
    
    cursor.execute('SELECT * FROM products WHERE flash_sale = TRUE')
    flash_sale_products = cursor.fetchall()

    return render_template('homepage.html', seller_products=seller_products, flash_sale_products=flash_sale_products)
    

# Route to display the registration page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Get form data
        email = request.form['email']
        password = request.form['password']
        role = 'user'  # Default role is 'customer'

        # Insert the user data into the MySQL database
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                '''INSERT INTO users (email, password, role) 
                VALUES (%s, %s, %s)''', (email, password, role)
            )
            conn.commit()

            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))

        except mysql.connector.Error as err:
            flash(f"Error: {err}", 'danger')
        finally:
            conn.close()

    return render_template('register.html')

# Route to display the login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        conn.close()
        
        session['logged_in'] = True
        
        if user and user[2] == password:
            session['user_id'] = user[0]
            session['role'] = user[3]  # Store the role
            role = user[3]

            flash('Login successful!', 'success')

            if role == 'superadmin':
                return redirect(url_for('superadmin_dashboard'))
            elif role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif role == 'seller':
                return redirect(url_for('sellerhomepage'))
            else:
                return redirect(url_for('homepage'))

        else:
            flash('Invalid email or password', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

# Route to handle logout functionality
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('homepage'))

# Admin route
@app.route('/admin_dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html')

# Superadmin route
@app.route('/superadmin_dashboard')
def superadmin_dashboard():
    return render_template('superadmin_dashboard.html')

@app.route('/sellerhomepage')
def sellerhomepage():
    if session.get('role') != 'seller':
        return redirect(url_for('sellerhomepage'))  # Redirect to a safe page (e.g., homepage)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT * FROM products WHERE seller_id IS NOT NULL')
    seller_products = cursor.fetchall()
    
    cursor.execute('SELECT * FROM products WHERE flash_sale = TRUE')
    flash_sale_products = cursor.fetchall()

    return render_template('sellerhomepage.html', seller_products=seller_products, flash_sale_products=flash_sale_products)

@app.route('/product')
def product():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT * FROM products WHERE seller_id IS NOT NULL')
    seller_products = cursor.fetchall()
    
    return render_template('product.html', seller_products=seller_products)
    

# Seller registration route
@app.route('/seller-registration', methods=['GET', 'POST'])
def seller_registration():
    if request.method == 'POST':
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        email = request.form['email']
        phonenumber = request.form['phonenumber']
        address = request.form['address']
        businessname = request.form['businessname']
        description = request.form['description']

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            query = """
                INSERT INTO sellers (firstname, lastname, email, phonenumber, address, businessname, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            values = (firstname, lastname, email, phonenumber, address, businessname, description)
            cursor.execute(query, values)
            conn.commit()

            flash('Seller registered successfully!', 'success')
            return redirect('/seller-registration')

        except mysql.connector.Error as err:
            flash(f"Error registering seller: {err}", 'danger')

        finally:
            conn.close()

    return render_template('seller_registration.html')

# Route to manage sellers
@app.route('/manage_sellers')
def manage_sellers():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT sellerid, firstname, lastname, email, phonenumber, address, businessname, description, createdtime, status 
            FROM sellers
        """)
        sellers = cursor.fetchall()

    except Exception as e:
        print(f"Error fetching sellers data: {e}")
        sellers = []

    finally:
        cursor.close()
        conn.close()

    return render_template('manage_sellers.html', sellers=sellers)

# Route to approve seller
@app.route('/approve_seller/<int:sellerid>', methods=['POST'])
def approve_seller(sellerid):
    conn = get_db_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("SELECT email FROM sellers WHERE sellerid = %s", (sellerid,))
        seller = cursor.fetchone()

        if seller is None:
            flash("Seller not found.", category="danger")
            return redirect(url_for('manage_sellers'))

        email = seller[0]

        query = "UPDATE sellers SET status = 'Approved' WHERE sellerid = %s"
        cursor.execute(query, (sellerid,))

        cursor.execute("UPDATE users SET role = %s WHERE email = %s", ('seller', email))

        conn.commit()

        flash("Seller approved successfully and role updated!", category="success")
        return redirect(url_for('manage_sellers'))

    except Error as e:
        flash(f"Error: {e}", category="danger")
        return redirect(url_for('manage_sellers'))

    finally:
        if conn:
            conn.close()

# Route to decline seller
@app.route('/decline_seller/<int:sellerid>', methods=['POST'])
def decline_seller(sellerid):
    conn = get_db_connection()

    try:
        cursor = conn.cursor()
        query = "UPDATE sellers SET status = 'Declined' WHERE sellerid = %s"
        cursor.execute(query, (sellerid,))
        conn.commit()

        flash("Seller declined successfully!", category="danger")
        return redirect(url_for('manage_sellers'))

    except Error as e:
        flash(f"Error: {e}", category="danger")
        return redirect(url_for('manage_sellers'))

    finally:
        if conn:
            conn.close()
            
#add products

@app.route('/add_product', methods=['POST'])
def add_product():
    product_name = request.form['product_name']
    product_description = request.form['product_description']
    product_price = request.form['product_price']
    product_stock = request.form['product_stock'] 
    product_category = request.form['product_category']
    product_color = request.form['product_color']
    product_image = request.files['product_image']

    discount_type = request.form.get('discount_type') 
    discount_value = request.form.get('product_discount', type=float)
    coupon_code = request.form.get('coupon_code') 
    
    flash_sale = request.form.get('flash_sale') == 'on' 
    
    if product_image and allowed_file(product_image.filename):
        filename = secure_filename(product_image.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        product_image.save(image_path)

        additional_images = request.files.getlist('additional_images')
        additional_image_paths = []
        for img in additional_images:
            if img and allowed_file(img.filename):
                additional_filename = secure_filename(img.filename)
                additional_image_path = os.path.join(app.config['UPLOAD_FOLDER'], additional_filename)
                img.save(additional_image_path)
                additional_image_paths.append(additional_filename)
                additional_images_json = json.dumps(additional_image_paths)

                user_id = session.get('user_id')
                conn = get_db_connection()
                cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO products (name, description, price, stock, image, category, seller_id, color, discount_type, discount_value, coupon_code, flash_sale, additional_images) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (product_name, product_description, product_price, product_stock, filename, product_category, user_id, product_color, discount_type, discount_value, coupon_code, flash_sale, additional_images_json))
            conn.commit()
            flash('Product added successfully!', 'success')
        except mysql.connector.Error as e:
            conn.rollback()
            flash(f'An error occurred while adding the product: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()
    else:
        flash('Invalid image file. Please upload a valid image (png, jpg, jpeg, gif).', 'error')

    return redirect(url_for('sellerhomepage'))

@app.route('/sellerdashboard')
def sellerdashboard():
    if session.get('role') != 'seller':
        return redirect(url_for('homepage'))  # Redirect to a safe page (e.g., homepage)
    return render_template('sellerdashboard.html')

@app.route('/productmanagement')
def productmanagement():
    return render_template('productmanagement.html')


#product details
@app.route('/products', methods=['GET'])
def product_listing():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT * FROM products')
    products = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('productdetails.html', products=products)

@app.route('/product/<int:product_id>', methods=['GET'])
def productdetails(product_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute('SELECT * FROM products WHERE id = %s', (product_id,))
        product = cursor.fetchone()

        if product:
            return render_template('productdetails.html', product=product)
        else:
            flash('Product not found.', 'error')
            return redirect(url_for('index'))

    except mysql.connector.Error as e:
        flash('An error occurred while retrieving product details.', 'error')
        print(f"Database error: {e}") 
        return redirect(url_for('index'))

    finally:
        cursor.close()
        conn.close()

    
@app.route('/laptop')
def laptop():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT * FROM products WHERE category = "Laptop"')
    seller_products = cursor.fetchall()
    
    return render_template('laptop.html', seller_products=seller_products)

@app.route('/cellphone')
def cellphone():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT * FROM products WHERE category = "Cellphone"')
    seller_products = cursor.fetchall()
    
    return render_template('cellphone.html', seller_products=seller_products)  

@app.route('/camera')
def camera():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT * FROM products WHERE category = "Camera"')
    seller_products = cursor.fetchall()
    
    return render_template('camera.html', seller_products=seller_products)     

@app.route('/inventorymanagement')
def inventorymanagement():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT * FROM products WHERE seller_id IS NOT NULL')
    seller_products = cursor.fetchall()
    
    return render_template('inventorymanagement.html', seller_products=seller_products) 

@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    product = get_product_by_id(product_id)
    if request.method == 'POST':
        product['name'] = request.form['product_name']
        product['description'] = request.form['product_description']
        product['price'] = float(request.form['product_price'])
        product['stock'] = int(request.form['product_stock'])
        product['category'] = (request.form['product_category'])
        product['color'] = request.form['product_color']
        product['discount_value'] = float(request.form['product_discount']) if request.form['product_discount'] else None
        product['discount_type'] = request.form['discount_type']
        

        if 'product_image' in request.files:
            file = request.files['product_image']
            new_image_filename = save_image(file)
            if new_image_filename:
                product['image'] = new_image_filename

        update_product_in_db(product) 
        flash('Product updated successfully!', 'success')
        return redirect(url_for('productdetails', product_id=product['id']))

    return render_template('edit_product.html', product=product)

  
@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check if the product exists before trying to delete
        cursor.execute('SELECT * FROM products WHERE id = %s', (product_id,))
        product = cursor.fetchone()

        if product is None:
            flash('Product not found.', 'error')
            return redirect(url_for('sellerdashboard'))

        # Delete the product
        cursor.execute('DELETE FROM products WHERE id = %s', (product_id,))
        conn.commit()
        flash('Product deleted successfully!', 'success')

        # Optionally, you can log notifications or other actions here
    except Exception as e:
        conn.rollback()
        flash(f'An error occurred while deleting the product: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('sellerdashboard'))

def update_product_in_db(product):
    """Update the product in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE products 
        SET name = %s, description = %s, price = %s, stock = %s, category = %s, color = %s,
            discount_value = %s, discount_type = %s, coupon_code = %s, image = %s
        WHERE id = %s
    ''', (product['name'], product['description'], product['price'], product['stock'],
          product['category'], product['color'], product['discount_value'], 
          product['discount_type'], product['coupon_code'], product['image'], product['id']))

    conn.commit()
    cursor.close()
    conn.close()


#add to cart 
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = int(data.get('quantity', 1))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM products WHERE id = %s', (product_id,))
    product = cursor.fetchone()
    cursor.close()
    conn.close()

    if product:
        if 'cart' not in session:
            session['cart'] = []


        price = float(product['price']) 

        for item in session['cart']:
            if item['id'] == product['id']:
                item['quantity'] += quantity
                item['subtotal'] = item['quantity'] * price
                break
        else:
            session['cart'].append({
                'id': product['id'],
                'name': product['name'],
                'variation': data.get('variation'),
                'price': price,
                'quantity': quantity,
                'subtotal': price * quantity,
                'image': product['image']
            })

        session.modified = True
        return jsonify({'success': True, 'cart': session['cart']})

    return jsonify({'success': False, 'error': 'Product not found'}), 404

#cart
@app.route('/cart', methods=['GET'])
def view_cart():
    user_id = session.get('user_id')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT c.id AS cart_id, ci.product_id, ci.quantity, p.name, p.price FROM carts c JOIN cart_items ci ON c.id = ci.cart_id JOIN products p ON ci.product_id = p.id WHERE c.user_id = %s', (user_id,))
    cart_items = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('cart.html', cart_items=cart_items)
if __name__ == '__main__':
    app.run(debug=True)
