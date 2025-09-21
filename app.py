from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
from utils import validate_username, validate_email, validate_login


app = Flask(__name__)
app.secret_key = "secret_key_5051"
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024

BASE_UPLOAD = Path("static/uploads")

app.config.update(
    UPLOADS={
        "profile_photos": BASE_UPLOAD / "profile_photos",
        "posts": BASE_UPLOAD / "posts",
        "files": BASE_UPLOAD / "files",
    }
)

for folder in app.config["UPLOADS"].values():
    Path(folder).mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif"}
"""def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
"""

def get_db_connection():
    conn = sqlite3.connect('app.db')
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/", methods=['GET', 'POST'])
def index():
    load_posts = int(request.args.get("load_posts", 10))
    scroll_to = request.args.get("scroll_to")
    if request.method == 'POST' and "more" in request.form:
        load_posts += 10
        scroll_to = request.form.get("scroll_to")
        return redirect(url_for("index", load_posts=load_posts, scroll_to=scroll_to))

    conn = get_db_connection()
    posts = conn.execute("""
                         SELECT p.*, u.username, u.id AS user_id
                         FROM posts p 
                         JOIN users u 
                         ON p.user_id = u.id
                         ORDER BY p.created_at DESC
                         
                         """).fetchmany(load_posts)
    conn.close()
    post_ids = [post['id'] for post in posts]
    user_ids = []
    for post in posts:
        if post['user_id'] not in user_ids:
            user_ids.append(post['user_id'])  
    profile_photos = {user_id: get_photo(user_id, 'profile_photos') for user_id in user_ids}
    
    image_paths = get_photos(post_ids)

    likes_data = {}
    for id in post_ids:
        likes = get_like(str(id))
        likes_data[id] = likes
    
    return render_template("index.html", posts=posts, load_posts=load_posts, 
                           scroll_to=scroll_to, image_paths=image_paths, 
                           likes_data=likes_data, profile_photos=profile_photos)


@app.route("/post/add", methods=['GET','POST'])
def add_post():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == "POST":
            user_id = session['user_id']
            title = request.form['title']
            content = request.form['content']
            image = request.files.get('file')

            conn = get_db_connection()
            conn.execute("INSERT INTO posts (user_id, title, content) VALUES (?, ?, ?)", (user_id, title, content))
            conn.commit()

            post_id = conn.execute("SELECT id FROM posts WHERE user_id = ? AND title = ?", (user_id, title)).fetchone()
            post_id = post_id[0]

            if image and image.filename:
                image = add_photo(post_id, image, 'posts')
            conn.close()
            return redirect(url_for('get_post', post_id=post_id))
    return render_template("post.html")


@app.route("/post/<post_id>")
def get_post(post_id):
    conn = get_db_connection()
    post = conn.execute(""" SELECT p.*, u.id AS user_id, u.username FROM posts p
                        JOIN users u ON p.user_id = u.id
                        WHERE p.id = ? """, (post_id,)).fetchone()
    conn.close()
    user_id = post['user_id']

    profile_photo = get_photo(user_id, 'profile_photos')

    image_path = get_photo(post_id, 'posts')

    likes = get_like(post_id)

    return render_template("post.html", post=post, image_path=image_path, likes=likes, profile_photo = profile_photo)


@app.route("/register", methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
     return redirect(url_for("profile"))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        validated_u = validate_username(username)
        validated_e = validate_email(email)

        if not username or not email or not password or validated_u or validated_e:
            error = "Пожалуйста заполните все поля"
            if validated_u and validated_e:
                error = f"{validated_u} и {validated_e}"
            elif validated_e or validated_u:
                error = f"{validated_u}{validated_e}"
            
            return render_template("register.html", error=error)
            

        hash_pw = generate_password_hash(password)

        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?) ", (username, email, hash_pw))
            conn.commit()
        except:
            error = "Ошибка: пользователь c таким именем или почтой уже существует!"
            return render_template("register.html", error = error)
        finally:
            conn.close()
        return redirect(url_for("login"))
        
    return render_template("register.html")


@app.route("/login", methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('profile'))
    
    error = None

    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        validated = validate_login(login)
        if validated:
            error = f"Неверное имя пользователя или email - ({login})"
            return render_template("login.html", error=error)
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ? OR email = ?", (login, login)).fetchone()
        conn.close()
        

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
            return redirect(url_for('profile'))
        else:
            error = "Неверное имя пользователя/email или пароль!"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/profile", methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect('login')
    if request.method == 'GET':
        user_id = session['user_id']
        conn = get_db_connection()
        posts = conn.execute("""
                            SELECT p.*, u.username 
                            FROM posts p 
                            JOIN users u 
                            ON p.user_id = u.id
                            ORDER BY p.created_at DESC
                            """).fetchall()
        conn.close()
        post_ids = [post['id'] for post in posts]
        image_paths = get_photos(post_ids)
        profile_photo = get_photo(user_id, 'profile_photos')
        likes_data = {}
        for id in post_ids:
            likes = get_like(str(id))
            likes_data[id] = likes

    elif request.method == 'POST':
        user_id = session['user_id']
        print(user_id)
        profile_photo = request.files.get('file')
        
        if profile_photo and profile_photo.filename:
            profile_photo = add_photo(user_id, profile_photo, 'profile_photos')
            return redirect(url_for('profile', profile_photo=profile_photo))
    return render_template("profile.html", posts=posts, image_paths=image_paths, likes_data=likes_data, profile_photo=profile_photo)

    
@app.route("/comments")
def get_comments():
    return render_template("comments.html")


@app.route("/uploads/posts/<filename>")
def serve_post_image(filename):
    folder = app.config["UPLOADS"]["posts"]
    return send_from_directory(str(folder), filename)


@app.route("/upload/profile_photos/<filename>")
def serve_profile_photo(filename):
    folder = app.config["UPLOADS"]["profile_photos"]
    return send_from_directory(str(folder), filename)


@app.route("/like/<post_id>", methods=['POST'])
def like_post(post_id):
    """post_id"""

    user_id = session['user_id']
    conn = get_db_connection()
    is_liked = conn.execute("SELECT id FROM likes WHERE user_id = ? AND post_id = ?", (user_id, post_id)).fetchone()
    if is_liked:
        conn.execute("DELETE FROM likes WHERE user_id = ? AND post_id = ?", (user_id, post_id))
    else: 
        conn.execute("INSERT INTO likes (user_id, post_id) VALUES (?, ?)",(user_id, post_id))
    conn.commit()
    conn.close()
    if request.form.get('next'):
        return redirect(url_for('index'))
    return redirect(url_for('get_post', post_id = post_id))


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


def add_photo(post_id, file, category):
    """
    post_id, file, str: category
    ) ->  str: filename
    """
    filename = secure_filename(file.filename)
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return None
    filename = f"{post_id}{ext}"
    folder = app.config["UPLOADS"][category]
    filepath = folder / filename
    file.filename = filename
    old_photo = get_photo(post_id, category)

    if old_photo:
        old_photo.unlink(missing_ok=False)

    file.save(filepath)
    return filename


def get_photo(post_id, category):
    """int: post_id
    """
    folder = Path(app.config["UPLOADS"][category])
    image_path = None
    for ext in ALLOWED_EXTENSIONS:
        candidate = folder / f"{post_id}{ext}"
        if candidate.exists():
            image_path = candidate
            break
    return image_path


def get_photos(post_ids):
    """list: post_ids
    """
    folder = Path(app.config["UPLOADS"]["posts"])

    image_paths = {}
    for post_id in post_ids:
        for ext in ALLOWED_EXTENSIONS:
            candidate = folder / f"{post_id}{ext}"
            if candidate.exists():
                image_paths[post_id] = candidate
                break
    return image_paths


if __name__ == ('__main__'):
    app.run(debug=True)