from flask import Flask, render_template, request, session, redirect
from flask_sqlalchemy import SQLAlchemy
# from werkzeug import secure_filename
from werkzeug.utils import secure_filename
# from werkzeug.datastructures import  FileStorage
from flask_mail import Mail
import json
import os
import math
from datetime import datetime

local_server = True
with open("config.json", "r") as conf:
    params = json.load(conf)["params"]

app = Flask(__name__)
app.secret_key = 'the-random-string-secret-key'
app.config["UPLOAD_FOLDER"] = params["uploaded_file_location"]
app.config.update(
    MAIL_SERVER="smtp.gmail.com",
    MAIL_PORT="465",
    MAIL_USE_SSL=True,
    MAIL_USERNAME=params["gmail-username"],
    MAIL_PASSWORD=params["gmail-password"]
)
mail = Mail(app)
if local_server:
    app.config["SQLALCHEMY_DATABASE_URI"] = params['local_uri']
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = params['prod_uri']
db = SQLAlchemy(app)


class Posts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, unique=True, nullable=False)
    content = db.Column(db.String, unique=False, nullable=False)
    author = db.Column(db.String, unique=False, nullable=False)
    date = db.Column(db.String)
    slug = db.Column(db.String)
    img_file = db.Column(db.String)
    tagline = db.Column(db.String)


class Contacts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=False, nullable=False)
    email = db.Column(db.String, unique=False, nullable=False)
    mobile_no = db.Column(db.String, unique=False, nullable=False)
    message = db.Column(db.String, unique=False, nullable=False)
    date = db.Column(db.String)


@app.route("/")
def home():
    posts = Posts.query.all()
    last = math.ceil(len(posts) / int(params['no_of_posts']))
    page = request.args.get('page')
    if not str(page).isnumeric():
        page = 1
    page = int(page)

    posts = posts[(page-1) * int(params['no_of_posts']):(page-1) * int(params['no_of_posts']) + int(params['no_of_posts'])]

    # pagination logic
    if page == 1:
        prev = "#"
        nex = "/?page=" + str(page + 1)
    elif page == last:
        prev = "/?page=" + str(page - 1)
        nex = "#"
    else:
        prev = "/?page=" + str(page - 1)
        nex = "/?page=" + str(page + 1)

    # posts = Posts.query.all()[0:params['no_of_posts']]
    return render_template("index.html", params=params, posts=posts, prev=prev, nex=nex)


@app.route("/about")
def about():
    return render_template("about.html", params=params)


@app.route("/dashboard", methods=['GET', 'POST'])
def dashboard():
    if 'user' in session and session['user'] == params['admin_username']:
        posts = Posts.query.all()
        return render_template('dashboard.html', params=params, posts=posts)

    if request.method == "POST":
        username = request.form.get('uname')
        password = request.form.get('upass')
        if username == params['admin_username'] and password == params['admin_password']:
            # set session variable
            session['user'] = username
            posts = Posts.query.all()
            return render_template('dashboard.html', params=params, posts=posts)
    else:
        return render_template("login.html", params=params)


@app.route("/logout")
def logout():
    session.pop('user')
    return redirect("/dashboard")


@app.route("/delete/<string:post_id>", methods=['GET', 'POST'])
def delete(post_id):
    if 'user' in session and session['user'] == params['admin_username']:
        post = Posts.query.filter_by(id=post_id).first()
        db.session.delete(post)
        db.session.commit()
    return redirect("/dashboard")


@app.route("/post/<string:post_slug>", methods=["GET"])
def post_route(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()
    return render_template("post.html", params=params, post=post)


@app.route("/uploader", methods=['GET', 'POST'])
def uploader():
    if 'user' in session and session['user'] == params['admin_username']:
        if request.method == 'POST':
            f = request.files['file1']
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))
            return "Uploaded successfully"


@app.route("/edit/<string:post_id>", methods=['GET', 'POST'])
def edit(post_id):
    if 'user' in session and session['user'] == params['admin_username']:
        if request.method == 'POST':
            req_title = request.form.get('title')
            req_tagline = request.form.get('tagline')
            req_slug = request.form.get('slug')
            req_content = request.form.get('content')
            img_file = request.form.get('img_file')
            date = datetime.now()

            if post_id == '0':
                post = Posts(title=req_title, tagline=req_tagline, slug=req_slug,
                             content=req_content, img_file=img_file, date=date)
                db.session.add(post)
                db.session.commit()

            else:
                post = Posts.query.filter_by(id=post_id).first()
                post.title = req_title
                post.tagline = req_tagline
                post.slug = req_slug
                post.content = req_content
                post.img_file = img_file
                post.date = date
                db.session.commit()
                return redirect('/edit/' + post_id)

        post = Posts.query.filter_by(id=post_id).first()
        return render_template('edit.html', params=params, post=post, post_id=post_id)


@app.route("/contact", methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        """ Add Entry to Database """
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')

        db.session.add(Contacts(name=name, email=email, mobile_no=phone, message=message, date=datetime.now()))
        db.session.commit()
        mail.send_message(
            "New mail from " + name,
            sender=email,
            recipients=[params['gmail-username']],
            body=message + "\n\n" + name + "\nMobile No." + phone
        )
    return render_template("contact.html", params=params)


app.run(debug=True)
