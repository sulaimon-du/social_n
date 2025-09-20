import re

def validate_username(username: str):
    username_pattern = r"^[a-zA-Z0-9._-]+$"
    if not re.match(username_pattern, username):
        return "Недопустимый username (разрешены только буквы, цифры, '-', '_' и '.')"
    return None

def validate_email(email: str):
    email_pattern = r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, email):
        return "Некорректный email"
    return None


def validate_login(login: str):
    login_pattern = r"^[a-zA-Z0-9._-]+(@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})?$"
    if not re.match(login_pattern, login):
        return True
    return None