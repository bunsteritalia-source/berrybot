import os
import json
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
from admin_site.auth import login_required, authenticate
from models import query_db, get_setting, set_setting
from werkzeug.security import generate_password_hash

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret')
UPLOAD_FOLDER = os.path.join('admin_site', 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.add_template_filter(lambda s: json.loads(s) if s else [], 'from_json')

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
    prods = query_db("""
        SELECT p.*, 
               (SELECT name_ru FROM categories WHERE id = p.category_id) as category_name,
               (SELECT MIN(price) FROM product_variants WHERE product_id = p.id) as min_price
        FROM products p
        ORDER BY p.id
    """)
    return render_template('products.html', products=prods)

@app.route('/products/add', methods=['GET', 'POST'])
@login_required
def product_add():
    if request.method == 'POST':
        name_ru = request.form.get('name_ru', '')
        name_en = request.form.get('name_en', '')
        name_ro = request.form.get('name_ro', '')
        desc_ru = request.form.get('desc_ru', '')
        desc_en = request.form.get('desc_en', '')
        desc_ro = request.form.get('desc_ro', '')
        category_id = request.form.get('category_id', '')
        base_price = request.form.get('base_price', 0)
        has_variants = 1 if request.form.get('has_variants') else 0
        photos = []
        for file in request.files.getlist('photos'):
            if file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                photos.append('/static/uploads/' + filename)

        if not name_ru or not category_id:
            return "Название (RU) и категория обязательны", 400

        product_id = query_db("INSERT INTO products (category_id, name_ru, name_en, name_ro, description_ru, description_en, description_ro, base_price, has_variants, photos) VALUES (?,?,?,?,?,?,?,?,?,?)",
                 [category_id, name_ru, name_en, name_ro, desc_ru, desc_en, desc_ro, base_price, has_variants, json.dumps(photos)], commit=True)
        product_id = query_db("SELECT last_insert_rowid()", one=True)[0]

        # Если выбран пресет, копируем его варианты
        preset_id = request.form.get('preset_id')
        if has_variants and preset_id:
            preset_variants = query_db("SELECT * FROM preset_variants WHERE preset_id = ?", [preset_id])
            for pv in preset_variants:
                query_db("INSERT INTO product_variants (product_id, name_ru, name_en, name_ro, price, quantity) VALUES (?,?,?,?,?,?)",
                         [product_id, pv['name_ru'], pv['name_en'], pv['name_ro'], pv['price'], pv['quantity']], commit=True)

        return redirect(url_for('products'))

    cats = query_db("SELECT * FROM categories")
    presets = query_db("SELECT * FROM presets")
    return render_template('product_form.html', product=None, categories=cats, presets=presets)

@app.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def product_edit(product_id):
    product = query_db("SELECT * FROM products WHERE id = ?", [product_id], one=True)
    if not product:
        return redirect(url_for('products'))
    if request.method == 'POST':
        name_ru = request.form.get('name_ru', '')
        name_en = request.form.get('name_en', '')
        name_ro = request.form.get('name_ro', '')
        desc_ru = request.form.get('desc_ru', '')
        desc_en = request.form.get('desc_en', '')
        desc_ro = request.form.get('desc_ro', '')
        category_id = request.form.get('category_id', '')
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

        # Если отмечено «заменить варианты из пресета»
        replace_preset = request.form.get('replace_preset')
        preset_id = request.form.get('preset_id')
        if replace_preset and preset_id:
            # Удаляем старые варианты
            query_db("DELETE FROM product_variants WHERE product_id = ?", [product_id], commit=True)
            # Добавляем из пресета
            preset_variants = query_db("SELECT * FROM preset_variants WHERE preset_id = ?", [preset_id])
            for pv in preset_variants:
                query_db("INSERT INTO product_variants (product_id, name_ru, name_en, name_ro, price, quantity) VALUES (?,?,?,?,?,?)",
                         [product_id, pv['name_ru'], pv['name_en'], pv['name_ro'], pv['price'], pv['quantity']], commit=True)

        return redirect(url_for('products'))

    cats = query_db("SELECT * FROM categories")
    presets = query_db("SELECT * FROM presets")
    variants = query_db("SELECT * FROM product_variants WHERE product_id = ?", [product_id])
    return render_template('product_form.html', product=product, categories=cats, presets=presets, current_variants=variants)

@app.route('/products/delete/<int:product_id>')
@login_required
def product_delete(product_id):
    query_db("DELETE FROM products WHERE id = ?", [product_id], commit=True)
    return redirect(url_for('products'))

# ... остальные маршруты (категории, админы, настройки, рассылка) остаются без изменений, они уже были. Я не буду их повторять для краткости, но в полном файле они должны быть. Ты можешь оставить их как есть, они не затрагиваются.
