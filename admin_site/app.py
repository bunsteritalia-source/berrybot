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
        return render_template('login.html', error='Неверные данные')
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

        query_db("INSERT INTO products (category_id, name_ru, name_en, name_ro, description_ru, description_en, description_ro, base_price, has_variants, photos) VALUES (?,?,?,?,?,?,?,?,?,?)",
                 [category_id, name_ru, name_en, name_ro, desc_ru, desc_en, desc_ro, base_price, has_variants, json.dumps(photos)], commit=True)
        product_id = query_db("SELECT last_insert_rowid()", one=True)[0]

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

        replace_preset = request.form.get('replace_preset')
        preset_id = request.form.get('preset_id')
        if replace_preset and preset_id:
            query_db("DELETE FROM product_variants WHERE product_id = ?", [product_id], commit=True)
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

# Варианты товара
@app.route('/products/<int:product_id>/variants')
@login_required
def variants(product_id):
    variants = query_db("SELECT * FROM product_variants WHERE product_id = ?", [product_id])
    product = query_db("SELECT * FROM products WHERE id = ?", [product_id], one=True)
    return render_template('variants.html', product=product, variants=variants)

@app.route('/products/<int:product_id>/variants/add', methods=['POST'])
@login_required
def variant_add(product_id):
    name_ru = request.form.get('name_ru', '')
    name_en = request.form.get('name_en', '')
    name_ro = request.form.get('name_ro', '')
    price = request.form.get('price', 0)
    quantity = request.form.get('quantity', 0)
    if not name_ru:
        name_ru = f'{quantity} шт'
    if not name_en:
        name_en = f'{quantity} pcs'
    if not name_ro:
        name_ro = f'{quantity} buc'
    query_db("INSERT INTO product_variants (product_id, name_ru, name_en, name_ro, price, quantity) VALUES (?,?,?,?,?,?)",
             [product_id, name_ru, name_en, name_ro, price, quantity], commit=True)
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
    name_en = request.form.get('name_en', '')
    name_ro = request.form.get('name_ro', '')
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
        text_ru = request.form.get('text_ru', '')
        text_en = request.form.get('text_en', '')
        text_ro = request.form.get('text_ro', '')
        photo = request.files.get('photo')
        photo_url = None
        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            photo_url = '/static/uploads/' + filename
        from broadcast import send_broadcast
        send_broadcast(text_ru, text_en, text_ro, photo_url)
        return render_template('broadcast.html', success=True)
    return render_template('broadcast.html')

# ========== ПРЕСЕТЫ ==========
@app.route('/presets')
@login_required
def presets():
    # Временный код: убедимся, что таблицы созданы (после восстановления старой базы)
    from db import init_db
    import asyncio
    loop = asyncio.new_event_loop()
    loop.run_until_complete(init_db())
    loop.close()
    # -------------------------------------------------

    all_presets = query_db("SELECT * FROM presets")
    return render_template('presets.html', presets=all_presets)

@app.route('/presets/add', methods=['POST'])
@login_required
def preset_add():
    name_ru = request.form.get('name_ru', '')
    name_en = request.form.get('name_en', '')
    name_ro = request.form.get('name_ro', '')
    if not name_ru:
        return "Название (RU) обязательно", 400
    query_db("INSERT INTO presets (name_ru, name_en, name_ro) VALUES (?,?,?)",
             [name_ru, name_en, name_ro], commit=True)
    return redirect(url_for('presets'))

@app.route('/presets/<int:preset_id>/variants')
@login_required
def preset_variants(preset_id):
    preset = query_db("SELECT * FROM presets WHERE id = ?", [preset_id], one=True)
    if not preset:
        return redirect(url_for('presets'))
    variants = query_db("SELECT * FROM preset_variants WHERE preset_id = ?", [preset_id])
    return render_template('preset_variants.html', preset=preset, variants=variants)

@app.route('/presets/<int:preset_id>/variants/add', methods=['POST'])
@login_required
def preset_variant_add(preset_id):
    quantity = request.form.get('quantity', 0)
    price = request.form.get('price', 0)
    name_ru = request.form.get('name_ru', f'{quantity} шт')
    name_en = request.form.get('name_en', f'{quantity} pcs')
    name_ro = request.form.get('name_ro', f'{quantity} buc')
    query_db("INSERT INTO preset_variants (preset_id, quantity, price, name_ru, name_en, name_ro) VALUES (?,?,?,?,?,?)",
             [preset_id, quantity, price, name_ru, name_en, name_ro], commit=True)
    return redirect(url_for('preset_variants', preset_id=preset_id))

@app.route('/preset_variants/delete/<int:variant_id>')
@login_required
def preset_variant_delete(variant_id):
    variant = query_db("SELECT * FROM preset_variants WHERE id = ?", [variant_id], one=True)
    if variant:
        query_db("DELETE FROM preset_variants WHERE id = ?", [variant_id], commit=True)
        return redirect(url_for('preset_variants', preset_id=variant['preset_id']))
    return redirect(url_for('presets'))

@app.route('/presets/delete/<int:preset_id>')
@login_required
def preset_delete(preset_id):
    query_db("DELETE FROM presets WHERE id = ?", [preset_id], commit=True)
    return redirect(url_for('presets'))
