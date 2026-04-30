from flask import Flask, render_template, redirect, request, flash, session, url_for
import sqlite3, re, hashlib
from flask import session
from datetime import datetime


app = Flask(__name__)

DB_NAME = "database.db"

import os
print("Using DB:", DB_NAME)
print("DB path:", os.path.abspath(DB_NAME))

app.secret_key = "secret123"  # needed for flash messages

# -------------------------
# DATABASE SETUP
# -------------------------
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    # ROLE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS role (
        role_id INTEGER PRIMARY KEY,
        role_name TEXT
    )
    """)
    cur.execute("INSERT OR IGNORE INTO role (role_id, role_name) VALUES (0, 'User')")
    cur.execute("INSERT OR IGNORE INTO role (role_id, role_name) VALUES (1, 'Producer')")



    # USER
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT,
        last_name TEXT,
        email TEXT UNIQUE,
        password_hash TEXT,
        phone_number TEXT,
        user_address TEXT,
        postcode TEXT,
        loyalty_points INTEGER DEFAULT 0,
        role_id INTEGER,
        FOREIGN KEY (role_id) REFERENCES role(role_id)
    )
    """)

    # PRODUCER
    cur.execute("""
    CREATE TABLE IF NOT EXISTS producer (
        producer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        business_name TEXT,
        business_description TEXT,
        join_date TEXT,
        farm_location TEXT,
        FOREIGN KEY (user_id) REFERENCES user(user_id)
    )
    """)

    # CATEGORY
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS category (
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_name TEXT,
        category_description TEXT
    )
    """)
    cur.execute("INSERT OR IGNORE INTO category (category_id, category_name) VALUES (1, 'Fresh Produce')")
    cur.execute("INSERT OR IGNORE INTO category (category_id, category_name) VALUES (2, 'Dairy & Eggs')")
    cur.execute("INSERT OR IGNORE INTO category (category_id, category_name) VALUES (3, 'Meat & Poultry')")
    cur.execute("INSERT OR IGNORE INTO category (category_id, category_name) VALUES (4, 'Bakery')")
    cur.execute("INSERT OR IGNORE INTO category (category_id, category_name) VALUES (5, 'Beverages')")
    cur.execute("INSERT OR IGNORE INTO category (category_id, category_name) VALUES (6, 'Organic')")
    cur.execute("INSERT OR IGNORE INTO category (category_id, category_name) VALUES (7, 'Seasonal Picks')")
    
    #SETTINGS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_preferences (
        user_id INTEGER PRIMARY KEY,
        theme TEXT DEFAULT 'light',
        text_size INTEGER DEFAULT 16,
        FOREIGN KEY (user_id) REFERENCES user(user_id)
    )
    """)


    # PRODUCT TABLE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS product (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        producer_id INTEGER,
        category_id INTEGER,
        product_name TEXT,
        description TEXT,
        price DECIMAL,
        stock_quantity INTEGER,
        unit TEXT,
        origin TEXT,
        quantity REAL,
        image_path TEXT,
        FOREIGN KEY (producer_id) REFERENCES producer(producer_id),
        FOREIGN KEY (category_id) REFERENCES category(category_id)
    )
    """)

    # Insert Marketplace producer
    cur.execute("""
    INSERT OR IGNORE INTO producer (producer_id, business_name, farm_location)
    VALUES (9999, 'Marketplace', 'N/A')
    """)

    


    # BASKET
    cur.execute("""
    CREATE TABLE IF NOT EXISTS basket (
        basket_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        FOREIGN KEY (user_id) REFERENCES user(user_id)
    )
    """)

    # BASKET ITEM
    cur.execute("""
    CREATE TABLE IF NOT EXISTS basket_item (
        basket_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        basket_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        FOREIGN KEY (basket_id) REFERENCES basket(basket_id),
        FOREIGN KEY (product_id) REFERENCES product(product_id)
    )
    """)

   # ORDER_ITEM TABLE
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        order_date TEXT,
        total_price REAL,
        delivery_method TEXT,
        delivery_address TEXT,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    );


    """)




    cur.execute("""
        CREATE TABLE IF NOT EXISTS order_item (
        order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        FOREIGN KEY(order_id) REFERENCES orders(order_id),
        FOREIGN KEY(product_id) REFERENCES product(product_id)
    );



    """)

    conn.commit()
    conn.close()

# -------------------------
# ROUTES
# -------------------------

@app.context_processor
def inject_user():
    user = None
    prefs = None

    if "user_id" in session:
        conn = get_db()
        cur = conn.cursor()

        # USER
        cur.execute("SELECT first_name, loyalty_points FROM user WHERE user_id=?", (session["user_id"],))
        row = cur.fetchone()

        # PREFS
        cur.execute("SELECT theme, text_size FROM user_preferences WHERE user_id=?", (session["user_id"],))
        prefs = cur.fetchone()

        conn.close()

        if row:
            user = {
                "first_name": row[0],
                "points": row[1],
            }

    return dict(user=user, prefs=prefs)


@app.route("/add_product", methods=["POST"])
def add_product():
    name = request.form.get("name", "").strip()
    price = request.form.get("price", "").strip()
    stock = request.form.get("stock", "").strip()
    quantity = request.form.get("quantity", "").strip()
    unit = request.form.get("unit", "").strip()
    category_id = request.form.get("category_id")

    conn = get_db()
    cur = conn.cursor()

    # get producer_id correctly
    cur.execute("SELECT producer_id FROM producer WHERE user_id=?", (session.get("user_id"),))


    row = cur.fetchone()

    if not row:
        flash("You are not registered as a producer", "product_error")
        conn.close()
        return redirect("/manage_products")

    producer_id = row[0]

    errors = []

    # validation...
    if not name: errors.append("Product name is required")
    if not price: errors.append("Price is required")
    if not stock: errors.append("Stock is required")
    if not quantity: errors.append("Quantity is required")
    if not category_id: errors.append("Category is required")

    try:
        price = float(price)
    except:
        errors.append("Price must be a number")

    try:
        stock = int(stock)
    except:
        errors.append("Stock must be a whole number")

    try:
        quantity = float(quantity)
    except:
        errors.append("Quantity must be a number")

    valid_units = [
        "g", "kg", "ml", "l",
        "pc", "item", "unit",
        "bottle", "jar", "bag", "box", "pack",
        "bunch", "punnet", "tray"
    ]

    if unit not in valid_units:
        errors.append("Invalid unit selected")


    if errors:
        for e in errors:
            flash(e, "product_error")
        conn.close()
        return redirect("/manage_products")


    products = cur.fetchall()
    for p in products:
        p["price"] = float(f"{p['price']:.2f}")

    cur.execute("""
    INSERT INTO product (
        producer_id,
        category_id,
        product_name,
        description,
        price,
        stock_quantity,
        unit,
        origin,
        quantity,
        image_path
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    producer_id,
    category_id,
    name,
    "",
    price,
    stock,
    unit,
    "",
    quantity,
    f"/static/images/{name.lower().replace(' ', '_')}.jpg"
))


    conn.commit()
    conn.close()

    flash("Product added successfully!", "success")
    return redirect("/manage_products")



def get_basket_items():
    user_id = session.get("user_id")
    if not user_id:
        return []

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT basket_id FROM basket WHERE user_id=?", (user_id,))
    basket = cur.fetchone()
    if not basket:
        return []

    basket_id = basket[0]

    cur.execute("""
        SELECT 
            product.product_id,
            product.product_name,
            product.price,
            product.image_path,
            producer.business_name,
            basket_item.quantity
        FROM basket_item
        JOIN product ON basket_item.product_id = product.product_id
        JOIN producer ON product.producer_id = producer.producer_id
        WHERE basket_item.basket_id=?
    """, (basket_id,))

    rows = cur.fetchall()
    conn.close()

    items = []
    for r in rows:
        items.append({
            "product_id": r[0],
            "product_name": r[1],
            "price": r[2],
            "image_path": r[3] or "/static/images/default.png",
            "producer_name": r[4],
            "quantity": r[5]
        })

    return items



@app.route("/delete_product/<int:id>")
def delete_product(id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM product WHERE product_id=?", (id,))

    conn.commit()
    conn.close()

    return redirect("/manage_products")

# Python: in your home route
@app.route("/")
def home():
    user_id = session.get("user_id")
    if not user_id:
        user = None
    if user_id:
        cur = get_db().cursor()
        cur.execute("SELECT user_id, first_name, loyalty_points FROM user WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        if row:
            user = {
                "user_id": row[0],
                "name": row[1],            # match template usage
                "points": row[2],
                "avatar_url": None         # optional placeholder
            }
    return render_template("home.html", producers=get_producers(), items=get_basket_items())

#For producer in "manage_products"
@app.route("/update_product", methods=["POST"])
def update_product():
    product_id = request.form.get("product_id")
    price = request.form.get("price")
    stock = request.form.get("stock_quantity")
    quantity = request.form.get("quantity")
    unit = request.form.get("unit")
    category_id = request.form.get("category_id")   # <-- FIX

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE product
        SET 
            price=?, 
            stock_quantity=?, 
            quantity=?, 
            unit=?, 
            category_id=?
        WHERE product_id=?
    """, (price, stock, quantity, unit, category_id, product_id))  # <-- FIX

    conn.commit()
    conn.close()

    return redirect("/manage_products")


@app.route("/about")
def about():
    
    return render_template("about.html", items=get_basket_items())


@app.route("/products_category")
def products_category():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM product")
    products = cur.fetchall()

    conn.close()
    return render_template("category_page.html", products=products, items=get_basket_items())



@app.route("/manage_products")
def manage_products():
    if session.get("role_id") != 1:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    # Get producer_id safely
    cur.execute("SELECT producer_id FROM producer WHERE user_id=?", (session["user_id"],))
    row = cur.fetchone()

    if not row:
        flash("You are not registered as a producer", "product_error")
        conn.close()
        return redirect("/")

    producer_id = row[0]

    # Fetch products
    cur.execute("""
        SELECT 
            product.product_id,
            product.product_name,
            product.price,
            product.stock_quantity,
            product.quantity,
            product.unit,
            category.category_name,
            producer.business_name,
            producer.farm_location
        FROM product
        JOIN producer ON product.producer_id = producer.producer_id
        JOIN category ON product.category_id = category.category_id
        WHERE product.producer_id = ?
    """, (producer_id,))
    products = cur.fetchall()

    # Fetch categories
    cur.execute("SELECT category_id, category_name FROM category")
    categories = cur.fetchall()

    conn.close()

    return render_template("manage_products.html", products=products, categories=categories)
# 

@app.route("/basket")
def basket():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            product.product_id,
            product.product_name,
            product.price,
            basket_item.quantity,
            product.image_path,
            producer.business_name AS producer_name
        FROM basket_item
        JOIN basket ON basket_item.basket_id = basket.basket_id
        JOIN product ON basket_item.product_id = product.product_id
        JOIN producer ON product.producer_id = producer.producer_id
        WHERE basket.user_id = ?
    """, (user_id,))


    items = cur.fetchall()
    conn.close()

    return render_template("basket_panel.html", items=items)




@app.route("/settings", methods=["GET", "POST"])
def settings():
    user_id = session.get("user_id")

    if not user_id:
        flash("Please log in to access settings.", "login_error")
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        theme = request.form.get("theme")
        text_size = request.form.get("text_size")

        first = request.form.get("first_name")
        last = request.form.get("last_name")
        phone = request.form.get("phone")
        email = request.form.get("email")
        address = request.form.get("address")
        postcode = request.form.get("postcode")

        # update user
        cur.execute("""
            UPDATE user
            SET first_name=?, last_name=?, phone_number=?, email=?, user_address=?, postcode=?
            WHERE user_id=?
        """, (first, last, phone, email, address, postcode, user_id))

        # update preferences
        cur.execute("""
            INSERT INTO user_preferences (user_id, theme, text_size)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                theme = excluded.theme,
                text_size = excluded.text_size
        """, (user_id, theme, text_size))

        conn.commit()
        conn.close()

        flash("Settings updated successfully!", "success")
        return redirect("/settings")

    # GET request
    cur.execute("""
        SELECT first_name, last_name, phone_number, email, user_address, postcode
        FROM user
        WHERE user_id=?
    """, (user_id,))
    user = cur.fetchone()

    cur.execute("SELECT theme, text_size FROM user_preferences WHERE user_id=?", (user_id,))
    prefs = cur.fetchone()

    conn.close()

    return render_template("settings.html", user=user, prefs=prefs)






@app.route("/order_history")
def orders():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    # Fetch all orders
    cur.execute("""
        SELECT order_id, order_date, total_price
        FROM orders
        WHERE user_id=?
        ORDER BY order_date DESC
    """, (user_id,))
    orders_data = cur.fetchall()

    history = []
    current_order = None

    for order_id, order_date, total_price in orders_data:

        # Fetch items for this order
        cur.execute("""
            SELECT p.product_name, oi.quantity
            FROM order_item oi
            JOIN product p ON oi.product_id = p.product_id
            WHERE oi.order_id=?
        """, (order_id,))
        items = [{"name": r[0], "qty": r[1]} for r in cur.fetchall()]

        history.append({
            "order_id": order_id,
            "order_date": order_date,
            "total_price": total_price,
            "order_items": items
        })

    if history:
        current_order = history[0]
        history = history[1:]

    conn.close()
    return render_template("order_history.html", current_order=current_order, history=history)

@app.route("/checkout")
def checkout():
    conn = get_db()
    cur = conn.cursor()

    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    # 1. Get basket_id
    cur.execute("SELECT basket_id FROM basket WHERE user_id=?", (user_id,))
    basket_id = cur.fetchone()[0]

    # 2. Fetch items
    cur.execute("""
        SELECT 
            p.product_id,
            p.product_name,
            p.price,
            bi.quantity,
            p.image_path,
            pr.business_name AS producer_name
        FROM basket_item bi
        JOIN product p ON bi.product_id = p.product_id
        JOIN producer pr ON p.producer_id = pr.producer_id
        WHERE bi.basket_id=?
    """, (basket_id,))

    rows = cur.fetchall()

    # 3. Convert to dictionaries for the template
    items = [
        {
            "id": r[0],
            "name": r[1],
            "price": r[2],
            "quantity": r[3],
            "image": r[4],
            "producer": r[5]
        }
        for r in rows
    ]

    # 4. Calculate total
    total = sum(item["price"] * item["quantity"] for item in items)

    conn.close()

    return render_template("checkout.html", items=items, total=total)



import hashlib

@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    password = request.form.get("password")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT user_id, password_hash, role_id FROM user WHERE email=?", (email,))
    user = cur.fetchone()

    if not user:
        flash("Invalid login", "login_error")
        return redirect("/")

    hashed = hashlib.sha256(password.encode()).hexdigest()

    if hashed != user[1]:
        flash("Invalid login", "login_error")
        return redirect("/")

    # Ensure user has a basket
    cur.execute("SELECT basket_id FROM basket WHERE user_id=?", (user[0],))
    basket = cur.fetchone()

    if not basket:
        cur.execute("INSERT INTO basket (user_id) VALUES (?)", (user[0],))
        conn.commit()

    session["user_id"] = user[0]
    session["role_id"] = user[2]

    # ⭐ FIX: store producer_id if this user is a producer
    if user[2] == 1:  # role_id == 1 means producer
        cur.execute("SELECT producer_id FROM producer WHERE user_id=?", (user[0],))
        producer = cur.fetchone()
        if producer:
            session["producer_id"] = producer[0]

    conn.close()
    return redirect("/")



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))  # ✅ correct




import hashlib

@app.route("/register", methods=["POST"])
def register():
    data = request.form

    first = data.get("first_name", "").strip()
    last = data.get("last_name", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    phone = data.get("phone", "").strip()
    address = data.get("address", "").strip()
    postcode = data.get("postcode", "").strip()

    errors = []

    # PRESENCE CHECKS
    if not first:
        errors.append("First name is required")
    if not last:
        errors.append("Last name is required")
    if not email:
        errors.append("Email is required")
    if not password:
        errors.append("Password is required")
    if not phone:
        errors.append("Phone number is required")
    if not address:
        errors.append("Address is required")
    if not postcode:
        errors.append("Postcode is required")

    # NAME VALIDATION – LETTERS ONLY
    if first and not re.match(r"^[A-Za-z]+$", first):
        errors.append("First name must contain letters only")

    if last and not re.match(r"^[A-Za-z]+$", last):
        errors.append("Last name must contain letters only")

    # ADDRESS VALIDATION – NO SPECIAL CHARACTERS
    # Allows letters, numbers, spaces, commas, periods, and hyphens
    if address and not re.match(r"^[A-Za-z0-9\s,.\-]+$", address):
        errors.append("Address contains invalid characters")

    # UK POSTCODE VALIDATION
    uk_postcode_pattern = r"^[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}$"
    if postcode and not re.match(uk_postcode_pattern, postcode.upper()):
        errors.append("Invalid UK postcode format")

    # LENGTH CHECKS
    if len(first) > 50:
        errors.append("First name too long")
    if len(password) < 6:
        errors.append("Password must be at least 6 characters")

    # EMAIL FORMAT
    if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        errors.append("Invalid email format")

    # PHONE NUMERIC
    if phone and not phone.isdigit():
        errors.append("Phone number must be numeric")

    # DATABASE CHECK
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM user WHERE email=?", (email,))
    existing = cur.fetchone()

    if existing:
        errors.append("Email already registered")

    # IF ERRORS → STOP
    if errors:
        for e in errors:
            flash(e, "register_error")
        conn.close()
        return redirect("/")

    # Assigning roles to users 
    role_id = 1 if data.get("is_producer") == "1" else 0

    # HASH THE PASSWORD
    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    # INSERT USER
    cur.execute("""
        INSERT INTO user 
        (first_name, last_name, email, password_hash, phone_number, user_address, postcode, role_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (first, last, email, hashed_password, phone, address, postcode, role_id))
    
    user_id = cur.lastrowid

    # USER PREFERENCES
    cur.execute("""
        INSERT INTO user_preferences (user_id, theme, text_size)
        VALUES (?, 'light', 16)
    """, (user_id,))

    # PRODUCER TABLE
    if role_id == 1:
        cur.execute("""
            INSERT INTO producer (user_id, business_name, business_description, join_date, farm_location)
            VALUES (?, ?, ?, ?, ?)
        """, (
            user_id,
            first,
            "Local producer",
            datetime.now().strftime("%d %B %Y"),
            "Unknown"
        ))

    conn.commit()
    conn.close()

    flash("Your account has been created successfully! Please log in.", "success")
    flash("open_login_modal", "modal")
    return redirect("/")





@app.route("/producers")
def producers_page():
    return render_template(
        "producers.html",
        producers=get_producers(),
        items=get_basket_items()
    )

    cur.execute("""
        SELECT 
            producer.producer_id AS id,
            producer.business_name AS name,
            producer.join_date AS joined,
            user.postcode AS postcode
        FROM producer
        JOIN user ON producer.user_id = user.user_id
    """)
    producers = cur.fetchall()




def get_producers():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            p.producer_id,
            u.first_name,
            u.last_name,
            p.business_name,
            p.join_date,
            p.farm_location,
            u.postcode
        FROM producer p
        JOIN user u ON p.user_id = u.user_id
    """)



    rows = cur.fetchall()
    conn.close()

    producers = []
    for r in rows:
        producers.append({
            "id": r[0],
            "name": f"{r[1]} {r[2]}",
            "business": r[3],
            "joined": r[4],
            "location": r[5],
            "postcode": r[6],
            "rating": 5
        })


    return producers


@app.route("/account")
def account():
    if "user_id" not in session and session.get("role_id") != 1:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT first_name FROM user WHERE user_id=?", (session["user_id"],))
    user = cur.fetchone()
    
    conn.close()

    return render_template("account.html", user=user)



@app.route("/products/<int:category_id>")
def category_page(category_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT 
        product.product_id,
        product.product_name AS name,
        product.price,
        product.quantity,
        product.stock_quantity,
        product.unit,
        producer.business_name AS producer
    FROM product
    JOIN producer ON product.producer_id = producer.producer_id
    WHERE product.category_id = ?
""", (category_id,))

    
    rows = cur.fetchall()

    products = []
    for r in rows:
        products.append({
            "id": r[0],
            "name": r[1],
            "price": r[2],
            "weight": r[3],
            "stock_quantity": r[4],
            "unit": r[5],
            "producer": r[6]
        })



    cur.execute("SELECT category_name FROM category WHERE category_id=?", (category_id,))
    category = cur.fetchone()

    conn.close()

    return render_template(
    "products.html",
    category=category[0],
    products=products,
    items=get_basket_items(),
    basket=session.get("basket", {}),
    basket_count=sum(session.get("basket", {}).values())
)



from flask import session, request, redirect, url_for

@app.route("/add_to_basket", methods=["POST"])
def add_to_basket():
    if "user_id" not in session:
        return {"error": "not_logged_in"}, 401

    data = request.get_json()
    product_id = int(data.get("product_id"))
    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor()

    # Get user's basket_id
    cur.execute("SELECT basket_id FROM basket WHERE user_id=?", (user_id,))
    basket = cur.fetchone()

    # If user has no basket, create one
    if not basket:
        cur.execute("INSERT INTO basket (user_id) VALUES (?)", (user_id,))
        conn.commit()
        cur.execute("SELECT basket_id FROM basket WHERE user_id=?", (user_id,))
        basket = cur.fetchone()

    basket_id = basket[0]

    # Check if item already exists
    cur.execute("""
        SELECT basket_item_id, quantity 
        FROM basket_item 
        WHERE basket_id=? AND product_id=?
    """, (basket_id, product_id))
    row = cur.fetchone()

    if row:
        # Increase quantity
        cur.execute("""
            UPDATE basket_item
            SET quantity = quantity + 1
            WHERE basket_item_id=?
        """, (row[0],))
    else:
        # Insert new item
        cur.execute("""
            INSERT INTO basket_item (basket_id, product_id, quantity)
            VALUES (?, ?, 1)
        """, (basket_id, product_id))

    print("USER ADDING:", session.get("user_id"))
    print("PRODUCT:", product_id)


    conn.commit()

    # fetch updated items
    cur = get_db().cursor()
    cur.execute("""
        SELECT 
            product.product_id,
            product.product_name,
            product.price,
            basket_item.quantity,
            product.image_path,
            producer.business_name AS producer_name
        FROM basket_item
        JOIN basket ON basket_item.basket_id = basket.basket_id
        JOIN product ON basket_item.product_id = product.product_id
        JOIN producer ON product.producer_id = producer.producer_id
        WHERE basket.user_id = ?
    """, (user_id,))
    items = cur.fetchall()

    return {"success": True}




@app.route("/update_qty", methods=["POST"])
def update_qty():
    if "user_id" not in session:
        return {"error": "not_logged_in"}, 401

    data = request.get_json()
    product_id = int(data.get("product_id"))
    action = data.get("action")
    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT basket_id FROM basket WHERE user_id=?", (user_id,))
    basket_id = cur.fetchone()[0]

    if action == "plus":
        cur.execute("""
            UPDATE basket_item
            SET quantity = quantity + 1
            WHERE basket_id=? AND product_id=?
        """, (basket_id, product_id))

    elif action == "minus":
        cur.execute("""
            UPDATE basket_item
            SET quantity = quantity - 1
            WHERE basket_id=? AND product_id=? AND quantity > 1
        """, (basket_id, product_id))

    conn.commit()
    conn.close()

    return {"success": True}





@app.route("/remove_item", methods=["POST"])
def remove_item():
    if "user_id" not in session:
        return {"error": "not_logged_in"}, 401

    data = request.get_json()
    product_id = int(data.get("product_id"))
    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT basket_id FROM basket WHERE user_id=?", (user_id,))
    basket_id = cur.fetchone()[0]

    cur.execute("""
        DELETE FROM basket_item
        WHERE basket_id=? AND product_id=?
    """, (basket_id, product_id))

    conn.commit()
    conn.close()

    return {"success": True}



@app.route("/basket_panel")
def basket_panel():
    if "user_id" not in session:
        return render_template("basket_panel.html", items=[])

    user_id = session["user_id"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            product.product_id,
            product.product_name,
            product.price,
            product.image_path,
            producer.business_name,
            basket_item.quantity
        FROM basket_item
        JOIN product ON basket_item.product_id = product.product_id
        JOIN producer ON product.producer_id = producer.producer_id
        WHERE basket_item.basket_id = (
            SELECT basket_id FROM basket WHERE user_id=?
        )
    """, (user_id,))

    rows = cur.fetchall()
    conn.close()

    items = [
        {
            "product_id": r[0],
            "product_name": r[1],
            "price": float(f"{r[2]:.2f}"),
            "image_path": r[3],
            "producer_name": r[4],
            "quantity": r[5],
        }
        for r in rows
    ]

    return render_template("basket_panel.html", items=items)


@app.route("/confirm_order", methods=["POST"])
def confirm_order():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    # Get basket_id
    cur.execute("SELECT basket_id FROM basket WHERE user_id=?", (user_id,))
    basket_id = cur.fetchone()[0]

    # Get basket items
    cur.execute("""
        SELECT product_id, quantity
        FROM basket_item
        WHERE basket_id=?
    """, (basket_id,))
    basket_items = cur.fetchall()

    # Calculate total
    cur.execute("""
        SELECT SUM(p.price * bi.quantity)
        FROM basket_item bi
        JOIN product p ON bi.product_id = p.product_id
        WHERE bi.basket_id=?
    """, (basket_id,))
    total = cur.fetchone()[0] or 0

    # Create order
    cur.execute("""
        INSERT INTO orders (user_id, order_date, total_price, delivery_method, delivery_address)
        VALUES (?, datetime('now'), ?, ?, ?)
    """, (user_id, total, "Delivery", "Sample Address"))

    order_id = cur.lastrowid

    # Insert items + reduce stock
    for product_id, qty in basket_items:
        # Insert into order_item
        cur.execute("""
            INSERT INTO order_item (order_id, product_id, quantity)
            VALUES (?, ?, ?)
        """, (order_id, product_id, qty))

        # Reduce stock
        cur.execute("""
            UPDATE product
            SET stock_quantity = MAX(stock_quantity - ?, 0)
            WHERE product_id = ?
        """, (qty, product_id))


    # Clear basket
    cur.execute("DELETE FROM basket_item WHERE basket_id=?", (basket_id,))

    conn.commit()
    conn.close()

    return redirect("/order_history")



@app.route("/thank_you")
def thank_you():
    order_items = session.get("order_items", [])
    total = session.get("order_total", 0)
    payment_method = session.get("payment_method", "Not specified")
    
    return render_template("thank_you.html", items=order_items, total=total, payment_method=payment_method)


@app.route("/producer/orders")
def producer_orders():
    role_id = session.get("role_id")
    producer_id = session.get("producer_id")
    
    


    if role_id != 1:
        return redirect("/")

    # Filters
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    category = request.args.get("category")

    conn = get_db()
    cur = conn.cursor()

    query = """
        SELECT DISTINCT o.order_id, o.order_date, 
               u.first_name || ' ' || u.last_name AS customer_name
        FROM orders o
        JOIN order_item oi ON o.order_id = oi.order_id
        JOIN product p ON oi.product_id = p.product_id
        JOIN user u ON o.user_id = u.user_id
        WHERE p.producer_id = ?
    """

    params = [producer_id]

    if date_from:
        query += " AND date(o.order_date) >= date(?)"
        params.append(date_from)

    if date_to:
        query += " AND date(o.order_date) <= date(?)"
        params.append(date_to)

    if category:
        query += " AND p.category_id = ?"
        params.append(int(category))

    query += " ORDER BY o.order_date DESC"

    cur.execute(query, params)
    order_rows = cur.fetchall()

    orders = []

    for row in order_rows:
        order_id = row["order_id"]

        cur.execute("""
            SELECT p.product_name, oi.quantity, p.price
            FROM order_item oi
            JOIN product p ON oi.product_id = p.product_id
            WHERE oi.order_id = ? AND p.producer_id = ?
        """, (order_id, producer_id))

        items = cur.fetchall()
        total = sum(i["quantity"] * i["price"] for i in items)

        orders.append({
            "order_id": order_id,
            "order_date": row["order_date"],
            "customer_name": row["customer_name"],
            "items": items,
            "total": total
        })

    conn.close()

    return render_template(
        "producer_orders.html",
        orders=orders,
        categories=get_categories()
    )




def get_categories():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT category_id, category_name FROM category")
    return cur.fetchall()


# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)