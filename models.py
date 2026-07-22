import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.getenv("DB_PATH", "berry.db")

def query_db(query, args=(), one=False, commit=False):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(query, args)
    if commit:
        conn.commit()
        conn.close()
        return
    rv = cur.fetchall()
    conn.close()
    return (rv[0] if rv else None) if one else rv

def get_all_users():
    rows = query_db("SELECT user_id FROM users")
    return [row['user_id'] for row in rows]

def get_setting(key):
    row = query_db("SELECT value FROM settings WHERE key = ?", [key], one=True)
    return row['value'] if row else ''

def set_setting(key, value):
    query_db("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", [key, value], commit=True)
