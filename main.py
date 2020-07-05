from flask import Flask, render_template, session, redirect
from flask_sqlalchemy import SQLAlchemy, request
from datetime import datetime
import json
from flask_mail import Mail

with open('config.json', 'r') as config:
    params = json.load(config)["params"]

if params['local_server']:
    uri = params['local_uri']
else:
    uri = params['prod_uri']

app = Flask(__name__)
app.secret_key = 'super-secret-key'
app.config.update(
    # gmail default smtp settings - https://support.google.com/mail/answer/7126229?hl=en
    MAIL_SERVER="smtp.gmail.com",
    MAIL_PORT=465,
    MAIL_USE_SSL=True,
    MAIL_USERNAME=params['gmail_user'],
    MAIL_PASSWORD=params['gmail_pw']
)
mail = Mail(app)

app.config['SQLALCHEMY_DATABASE_URI'] = uri
db = SQLAlchemy(app)


class Posts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), unique=True, nullable=False)
    subtitle = db.Column(db.String(120), unique=False, nullable=False)
    slug = db.Column(db.String(11), unique=True, nullable=False)
    content = db.Column(db.String(120), unique=True, nullable=False)
    date = db.Column(db.String(12), unique=True, nullable=True)


class Feedback(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=False, nullable=False)
    email = db.Column(db.String(120), unique=False, nullable=False)
    phone_no = db.Column(db.String(11), unique=False, nullable=False)
    message = db.Column(db.String(120), unique=False, nullable=False)
    date = db.Column(db.String(12), unique=True, nullable=False)


@app.route('/')
def home():
    from math import ceil
    posts = Posts.query.filter_by().all()
    last = ceil(len(posts)/params['home_posts'])

    page = request.args.get('page')
    if page is None:
        page = 1
    else:
        page = int(page)

    display_posts = posts[(page-1)*params['home_posts']: (page-1)*params['home_posts']+params['home_posts']]

    if page == 1:
        prev_page = '#'
        next_page = '?page='+str(page+1)
    elif 1 < page < last:
        prev_page = '?page='+str(page-1)
        next_page = '?page='+str(page+1)
    elif page == last:
        prev_page = '?page='+str(page-1)
        next_page = '#'
    else:
        prev_page = '#'
        next_page = '#'

    return render_template('index.html', params=params, posts=display_posts, prev=prev_page, next=next_page)


@app.route('/about')
def about():
    return render_template('about.html', params=params)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')

        entry = Feedback(name=name, email=email, phone_no=phone, message=message, date=datetime.now())
        db.session.add(entry)
        db.session.commit()
        # Enable access to less secure apps in gmail account to get an email
        mail.send_message("New message from" + name,
                          sender=email,
                          recipients=[params['gmail_user']],
                          body="{sender} has contacted you and sent you the following message on your "
                               "site\n\n{message}\n\n{sender} can be reached out at {phone_num} or "
                               "{email}".format(sender=name, message=message, phone_num=phone, email=email))

    return render_template('contact.html', params=params)


@app.route('/post/<string:post_slug>')
def post_route(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()
    return render_template('post.html', params=params, post=post)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session and session['user'] == params['admin_user']:
        posts = Posts.query.filter_by().all()
        return render_template('admin.html', params=params, posts=posts)

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == params['admin_user'] and password == params['admin_password']:
            session['user'] = username
            posts = Posts.query.filter_by().all()
            return render_template('admin.html', params=params, posts=posts)

    return render_template('login.html', params=params)


@app.route('/edit/<string:sno>', methods=['GET', 'POST'])
def edit(sno):
    if 'user' in session and session['user'] == params['admin_user']:
        if request.method == 'POST':
            title = request.form.get('title')
            subtitle = request.form.get('subtitle')
            slug = request.form.get('slug')
            content = request.form.get('content')
            date = datetime.now()

            # Add a new post
            if sno == '0':
                new_post = Posts(title=title, subtitle=subtitle, slug=slug, content=content, date=date)
                db.session.add(new_post)
                db.session.commit()
                return redirect('/login')
            # Edit existing post
            else:
                post = Posts.query.filter_by(sno=sno).first()
                post.title = title
                post.subtitle = subtitle
                post.slug = slug
                post.content = content
                post.date = date
                db.session.commit()
                return redirect('/login')
        else:
            post = Posts.query.filter_by(sno=sno).first()
            return render_template('edit.html', params=params, post=post, sno=sno)


@app.route('/delete/<string:sno>')
def delete(sno):
    if 'user' in session and session['user'] == params['admin_user']:
        post = Posts.query.filter_by(sno=sno).first()
        db.session.delete(post)
        db.session.commit()
        return redirect('/login')


app.run()
