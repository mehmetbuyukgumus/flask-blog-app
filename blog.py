from flask import Flask,render_template, flash, redirect, url_for, session, logging,request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

# Kullanıcı Giriş Decorator'u
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntümek için lütfen giriş yapın", "danger")
            return redirect(url_for("login"))
    return decorated_function

class RegisterForm(Form):
    name = StringField("İsim Soyisim", validators=[validators.Length(min=4, max=25)])
    username = StringField("Kullanıcı Adı", validators=[validators.Length(min=5, max=35)])
    email = StringField("E-Mail Adresi")
    password = PasswordField("Parola", validators = [
        validators.DataRequired("Lütfen bir parola belirleyin"),
        validators.EqualTo(fieldname = "confirm", message="Parolanız uyuşmuyor")
    ])
    confirm = PasswordField("Parola doğrula")

# validators.email(message="Lütfen geçerli bir email adresi giriniz")

class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")

class ArticleForm(Form):
    title = StringField("Makale Başlığı", validators=[validators.Length(min=5, max=100)])
    content = TextAreaField("Makale İçeriği", validators=[validators.Length(min=10)])

app = Flask(__name__)
app.secret_key = "ybblog"

app.config["MYSQL_HOST"] = "127.0.0.1"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "ybblog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"
app.config["MYSQL_UNIX_SOCKET"] = "/var/run/mysqld/mysqld.sock"


mysql = MySQL(app)

@app.route("/")
def index():
    articles = [
        {"id": 1, "title": "Deneme1", "content": "Deneme1 içerik"},
        {"id": 2, "title": "Deneme2", "content": "Deneme2 içerik"},
        {"id": 3, "title": "Deneme3", "content": "Deneme3 içerik"}
               ]
    return render_template("index.html", articles=articles)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    query = "SELECT * FROM articles"
    result = cursor.execute(query)
    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html", articles = articles)
    else:
        return render_template("articles.html")
    
@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    query = "SELECT * FROM articles WHERE id = %s"
    result = cursor.execute(query,(id,))
    if result > 0:
        article = cursor.fetchone()
        return render_template("/article.html", article = article)
    else:
        return render_template("/article.html")

@app.route("/register", methods= ["GET", "POST"])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)      
        cursor = mysql.connection.cursor()
        query = "INSERT INTO users(name,email,username,password) VALUES (%s,%s,%s,%s)"
        cursor.execute(query,(name,email,username,password))
        mysql.connection.commit()
        cursor.close()
        flash("Başarıyla Kayıt Oldunuz", "success")
        
        return redirect(url_for("login"))
    else:
        return render_template("register.html",form=form)
    
@app.route("/login", methods = ["GET", "POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        password_entered = form.password.data
        cursor = mysql.connection.cursor()
        query = "SELECT * FROM users WHERE username = %s"
        result = cursor.execute(query, (username,))
        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password_entered, real_password):
                flash("Başarıyla giriş yaptınız", "success")
                session["logged_in"] = True
                session["username"] = username
                
                return redirect(url_for("index"))
        else:
            flash("Böyle bir kullanıcı yok...", "danger")
            return redirect(url_for("login"))
    return render_template("login.html", form=form)   
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    query = "SELECT * FROM articles WHERE author=%s"
    result = cursor.execute(query,(session["username"],))
    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html", articles=articles)
    else:
        return render_template("dashboard.html")

@app.route("/addarticle", methods = ["GET", "POST"])
def addarticle():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data
        
        cursor = mysql.connection.cursor()
        query = "INSERT INTO articles(title,author,content) VALUES (%s,%s,%s)"
        cursor.execute(query,(title, session["username"], content))
        mysql.connection.commit()
        cursor.close()
        
        flash("Makale Başarıyla Eklendi", "success")
        return redirect(url_for("dashboard"))
        
        
    return render_template("addarticle.html", form=form)

@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    query = "SELECT * FROM articles WHERE author = %s AND id = %s"
    result = cursor.execute(query,(session["username"], id))
    if result > 0:
        query2 = "DELETE FROM articles WHERE id = %s"
        cursor.execute(query2, (id,))
        mysql.connection.commit()
        flash("Makale başarıyla silindi", "danger")
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale bulunamamaktadır veya bu işleme yetkiniz bulunmamaktadır.", "danger")
        return redirect(url_for("dashboard"))

@app.route("/edit/<string:id>", methods = ["GET", "POST"])
@login_required
def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        query = "SELECT * FROM articles WHERE id = %s AND author = %s"
        result = cursor.execute(query,(id, session["username"]))
        if result == 0:
            flash("Böyle bir makale yok veya bu işleme yetkiniz yok", "danger")
            return redirect(url_for("index"))            
        else:
            article = cursor.fetchone()
            form = ArticleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html", form=form)
    else:
        form = ArticleForm(request.form)
        newTitle = form.title.data
        newContent = form.content.data
        query = "UPDATE articles SET title = %s, content = %s WHERE id = %s"
        cursor = mysql.connection.cursor()
        cursor.execute(query,(newTitle, newContent, id))
        mysql.connection.commit()
        flash("Makale başarıyla güncellendi", "success")
        return redirect(url_for("dashboard"))

@app.route("/search", methods = ["GET", "POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")
        cursor = mysql.connection.cursor()
        query = "SELECT * FROM articles WHERE title LIKE %s"
        result = cursor.execute(query, ('%' + keyword + '%',))
        if result == 0:
            flash("Aranan kelimeye uygun makale bulunamadı", "warning")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            return render_template("/articles.html", articles=articles)        

if __name__ == "__main__":
    app.run(debug=True)
