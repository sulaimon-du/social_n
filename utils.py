import re

from flask import session
from wtforms.validators import ValidationError

from instance.db_connect import get_db_connection

def validate_username(username: str):
    username_pattern = r"^[a-zA-Z0-9._-]+$"
    if not re.match(username_pattern, username):
        return "Недопустимый username (разрешены только буквы, цифры, '-', '_' и '.')"
    elif len(username) < 8 or len(username) > 30:
            return "Имя пользователя должно состоять от 8 до 30 символов"
    return None

def validate_email(email: str):
    email_pattern = r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, email):
        return "Некорректный email"
    return ''


def validate_login(login: str):
    login_pattern = r"^[a-zA-Z0-9._-]+(@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})?$"
    if not re.match(login_pattern, login):
        return True
    return ''

def get_like(post_id):
    """post_id -> dict: (is_liked, likes)"""
    if 'user_id' not in session:
        user_id = 0
    else:
        user_id = session['user_id']
    conn = get_db_connection()
    is_liked = conn.execute("SELECT id FROM likes WHERE user_id = ? AND post_id = ?", (user_id, post_id)).fetchone()
    likes_count = conn.execute("SELECT count(id) FROM likes WHERE post_id = ?", (post_id,)).fetchone()
    conn.close()
    return { 'is_liked': bool(is_liked), 'likes': likes_count[0] }

def user_exist(login):
    """int: login(user_name/email)"""
    conn = get_db_connection()
    user_name = conn.execute("SELECT id FROM users WHERE username=? OR email=?", (login, login)).fetchone()
    conn.close()
    if user_name and '@' in login:
        return 'email'
    elif user_name:
        return 'username'
    else:
        return ''
    
username = 'hahaha'

