from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from future.is_allowed import validate_username, validate_email, validate_login


app = Flask(__name__)
app.secret_key = "secret_key_5051"

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
    posts = conn.execute("SELECT * FROM posts").fetchmany(load_posts)
    conn.close()

    return render_template("index.html", posts=posts, load_posts=load_posts, scroll_to=scroll_to)


@app.route("/post/add", methods=['GET','POST'])
def add_post():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == "POST":
            user_id = session['user_id']
            title = request.form['title']
            content = request.form['content']
            conn = get_db_connection()
            conn.execute("INSERT INTO posts (user_id, title, content) VALUES (?, ?, ?)", (user_id, title, content))
            conn.commit()
            post_id = conn.execute("SELECT id FROM posts WHERE user_id = ? AND title = ?", (user_id, title)).fetchone()
            post_id = post_id[0]
            conn.close()
            return redirect(url_for('get_post', post_id=post_id))
    return render_template("post.html")


@app.route("/post/<post_id>")
def get_post(post_id):
    conn = get_db_connection()
    post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    conn.close()
    return render_template("post.html", post=post)


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

@app.route("/profile")
def profile():
    if 'user_id' not in session:
        return redirect('login')
    return render_template("profile.html")

    
@app.route("/comments")
def get_comments():
    return render_template("comments.html")

if __name__ == ('__main__'):
    app.run(debug=True)