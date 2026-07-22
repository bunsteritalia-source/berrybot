import aiosqlite
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.getenv("DB_PATH", "berry.db")

async def get_db():
    return await aiosqlite.connect(DB_PATH)

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name_ru TEXT,
                name_en TEXT,
                name_ro TEXT
            );
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER,
                name_ru TEXT,
                name_en TEXT,
                name_ro TEXT,
                description_ru TEXT,
                description_en TEXT,
                description_ro TEXT,
                base_price INTEGER DEFAULT 0,
                has_variants INTEGER DEFAULT 0,
                photos TEXT DEFAULT '[]',
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            );
            CREATE TABLE IF NOT EXISTS product_variants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                name_ru TEXT,
                name_en TEXT,
                name_ro TEXT,
                price INTEGER,
                quantity INTEGER DEFAULT 0,
                FOREIGN KEY (product_id) REFERENCES products(id)
            );
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password_hash TEXT,
                telegram_id INTEGER,
                notify_orders INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                items TEXT,
                total_price INTEGER,
                customer_name TEXT,
                phone TEXT,
                telegram_username TEXT,
                delivery_method TEXT,
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS cart (
                user_id INTEGER,
                product_id INTEGER,
                variant_id INTEGER,
                quantity INTEGER,
                PRIMARY KEY (user_id, product_id, variant_id)
            );
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                language TEXT DEFAULT 'en'
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            INSERT OR IGNORE INTO settings (key, value) VALUES 
                ('info_text_ru', ''),
                ('info_text_en', ''),
                ('info_text_ro', ''),
                ('info_image', ''),
                ('site_url', 'https://berry.md/'),
                ('facebook_url', 'https://www.facebook.com/berry.bouquet.md/'),
                ('instagram_url', 'https://www.instagram.com/berry_bouquet.md/'),
                ('tiktok_url', 'https://www.tiktok.com/@berry_bouquet_md.md');
        """)
        # Удаляем старого админа и создаём нового с паролем admin123
        await db.execute("DELETE FROM admins WHERE username = 'admin'")
        hashed = generate_password_hash('admin123')
        await db.execute("INSERT OR IGNORE INTO admins (username, password_hash) VALUES (?, ?)", ('admin', hashed))
        await db.commit()
