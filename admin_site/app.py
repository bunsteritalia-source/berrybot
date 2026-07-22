import os
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
from admin_site.auth import login_required, authenticate
from models import query_db, get_setting, set_setting
from werkzeug.security import generate_password_hash
import json

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret')
UPLOAD_FOLDER = os.path.join('admin_site', 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = authenticate(username, password)
        if admin:
            session['admin_id'] = admin['id']
            return redirect(url_for('dashboard'))
        return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_id', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')

# --- Товары ---
@app.route('/products')
@login_required
def products():
    prods = query_db("SELECT * FROM products ORDER BY id")
    return render_template('products.html', products=prods)

@app.route('/products/add', methods=['GET', 'POST'])
@login_required
def product_add():
    if request.method == 'POST':
        name_ru = request.form['name_ru']
        name_en = request.form['name_en']
        name_ro = request.form['name_ro']
        desc_ru = request.form.get('desc_ru', '')
        desc_en = request.form.get('desc_en', '')
        desc_ro = request.form.get('desc_ro', '')
        category_id = request.form['category_id']
        base_price = request.form.get('base_price', 0)
        has_variants = 1 if request.form.get('has_variants') else 0
        photos = []
        for file in request.files.getlist('photos'):
            if file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                photos.append('/static/uploads/' + filename)
        query_db("INSERT INTO products (category_id, name_ru, name_en, name_ro, description_ru, description_en, description_ro, base_price, has_variants, photos) VALUES (?,?,?,?,?,?,?,?,?,?)",
                 [category_id, name_ru, name_en, name_ro, desc_ru, desc_en, desc_ro, base_price, has_variants, json.dumps(photos)], commit=True)
        return redirect(url_for('products'))
    cats = query_db("SELECT * FROM categories")
    return render_template('product_form.html', product=None, categories=cats)

@app.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def product_edit(product_id):
    product = query_db("SELECT * FROM products WHERE id = ?", [product_id], one=True)
    if not product:
        return redirect(url_for('products'))
    if request.method == 'POST':
        name_ru = request.form['name_ru']
        name_en = request.form['name_en']
        name_ro = request.form['name_ro']
        desc_ru = request.form.get('desc_ru', '')
        desc_en = request.form.get('desc_en', '')
        desc_ro = request.form.get('desc_ro', '')
        category_id = request.form['category_id']
        base_price = request.form.get('base_price', 0)
        has_variants = 1 if request.form.get('has_variants') else 0
        photos = json.loads(product['photos']) if product['photos'] else []
        for file in request.files.getlist('photos'):
            if file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                photos.append('/static/uploads/' + filename)
        query_db("UPDATE products SET category_id=?, name_ru=?, name_en=?, name_ro=?, description_ru=?, description_en=?, description_ro=?, base_price=?, has_variants=?, photos=? WHERE id=?",
                 [category_id, name_ru, name_en, name_ro, desc_ru, desc_en, desc_ro, base_price, has_variants, json.dumps(photos), product_id], commit=True)
        return redirect(url_for('products'))
    cats = query_db("SELECT * FROM categories")
    return render_template('product_form.html', product=product, categories=cats)

@app.route('/products/delete/<int:product_id>')
@login_required
def product_delete(product_id):
    query_db("DELETE FROM products WHERE id = ?", [product_id], commit=True)
    return redirect(url_for('products'))

# Варианты
@app.route('/products/<int:product_id>/variants')
@login_required
def variants(product_id):
    variants = query_db("SELECT * FROM product_variants WHERE product_id = ?", [product_id])
    product = query_db("SELECT * FROM products WHERE id = ?", [product_id], one=True)
    return render_template('variants.html', product=product, variants=variants)

@app.route('/products/<int:product_id>/variants/add', methods=['POST'])
@login_required
def variant_add(product_id):
    name_ru = request.form['name_ru']
    name_en = request.form['name_en']
    name_ro = request.form['name_ro']
    price = request.form['price']
    query_db("INSERT INTO product_variants (product_id, name_ru, name_en, name_ro, price) VALUES (?,?,?,?,?)",
             [product_id, name_ru, name_en, name_ro, price], commit=True)
    return redirect(url_for('variants', product_id=product_id))

@app.route('/variants/delete/<int:variant_id>')
@login_required
def variant_delete(variant_id):
    variant = query_db("SELECT * FROM product_variants WHERE id = ?", [variant_id], one=True)
    if variant:
        query_db("DELETE FROM product_variants WHERE id = ?", [variant_id], commit=True)
        return redirect(url_for('variants', product_id=variant['product_id']))
    return redirect(url_for('products'))

# Категории
@app.route('/categories')
@login_required
def categories():
    cats = query_db("SELECT * FROM categories")
    return render_template('categories.html', categories=cats)

@app.route('/categories/add', methods=['POST'])
@login_required
def category_add():
    name_ru = request.form['name_ru']
    name_en = request.form['name_en']
    name_ro = request.form['name_ro']
    query_db("INSERT INTO categories (name_ru, name_en, name_ro) VALUES (?,?,?)", [name_ru, name_en, name_ro], commit=True)
    return redirect(url_for('categories'))

@app.route('/categories/delete/<int:cat_id>')
@login_required
def category_delete(cat_id):
    query_db("DELETE FROM categories WHERE id = ?", [cat_id], commit=True)
    return redirect(url_for('categories'))

# Администраторы
@app.route('/admins')
@login_required
def admins():
    admins = query_db("SELECT * FROM admins")
    return render_template('admins.html', admins=admins)

@app.route('/admins/add', methods=['POST'])
@login_required
def admin_add():
    username = request.form['username']
    password = request.form['password']
    telegram_id = request.form.get('telegram_id', '')
    notify = 1 if request.form.get('notify_orders') else 0
    hashed = generate_password_hash(password)
    query_db("INSERT INTO admins (username, password_hash, telegram_id, notify_orders) VALUES (?,?,?,?)",
             [username, hashed, telegram_id, notify], commit=True)
    return redirect(url_for('admins'))

@app.route('/admins/delete/<int:admin_id>')
@login_required
def admin_delete(admin_id):
    query_db("DELETE FROM admins WHERE id = ?", [admin_id], commit=True)
    return redirect(url_for('admins'))

@app.route('/admins/toggle_notify/<int:admin_id>')
@login_required
def admin_toggle_notify(admin_id):
    admin = query_db("SELECT * FROM admins WHERE id = ?", [admin_id], one=True)
    if admin:
        new_val = 0 if admin['notify_orders'] else 1
        query_db("UPDATE admins SET notify_orders = ? WHERE id = ?", [new_val, admin_id], commit=True)
    return redirect(url_for('admins'))

# Настройки
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        for key in ['info_text_ru', 'info_text_en', 'info_text_ro',
                    'site_url', 'facebook_url', 'instagram_url', 'tiktok_url']:
            set_setting(key, request.form.get(key, ''))
        file = request.files.get('info_image')
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            set_setting('info_image', '/static/uploads/' + filename)
        return redirect(url_for('settings'))
    config = {}
    for key in ['info_text_ru', 'info_text_en', 'info_text_ro', 'info_image',
                'site_url', 'facebook_url', 'instagram_url', 'tiktok_url']:
        config[key] = get_setting(key)
    return render_template('settings.html', config=config)

# Рассылка
@app.route('/broadcast', methods=['GET', 'POST'])
@login_required
def broadcast():
    if request.method == 'POST':
        text_ru = request.form['text_ru']
        text_en = request.form['text_en']
        text_ro = request.form['text_ro']
        photo = request.files.get('photo')
        photo_url = None
        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            photo_url = '/static/uploads/' + filename
        from broadcast import send_broadcast
        send_broadcast(text_ru, text_en, text_ro, photo_url)
        return render_template('broadcast.html', success=True)
    return render_template('broadcast.html')
