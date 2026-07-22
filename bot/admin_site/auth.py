from functools import wraps
from flask import session, redirect, url_for
from models import query_db
from werkzeug.security import check_password_hash

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def authenticate(username, password):
    user = query_db("SELECT * FROM admins WHERE username = ?", [username], one=True)
    if user and check_password_hash(user['password_hash'], password):
        return user
    return None
