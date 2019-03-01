from flask import Flask, render_template, redirect, url_for, flash, request
import requests
import csv
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo
from flask_bcrypt import Bcrypt
from flask_login import UserMixin, LoginManager, login_user, current_user, logout_user, login_required

app = Flask(__name__)
app.config['SECRET_KEY']="get yours"
POSTGRES = {
    'user': 'postgres',
    'pw': 'tunga',
    'db': 'project1',
    'host': 'localhost',
    'port': '5432',
}

app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{POSTGRES['user']}:{POSTGRES['pw']}@{POSTGRES['host']}:{POSTGRES['port']}/{POSTGRES['db']}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

#models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    #posts = db.relationship('Post', backref='author', lazy=True, cascade="all, delete-orphan")#this is a relationship not a column
    reviews = db.relationship('Review', backref='reviewer', lazy=True, cascade="all, delete-orphan")#this is a relationship not a column


class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    isbn = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    year = db.Column(db.String(100), nullable=False)
    #user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reviews = db.relationship('Review', backref='author', lazy=True, cascade="all, delete-orphan")#this is a relationship not a column


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    comment = db.Column(db.Text, nullable=False)
    rating = db.Column(db.String(100), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


#forms
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class ReviewForm(FlaskForm):
    comment = TextAreaField('Comment', validators=[DataRequired()])
    rating = StringField('Rating', validators=[DataRequired(), Length(max=1)])
    submit = SubmitField('Review')

#routes
@app.route("/", methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        pw_hash = bcrypt.generate_password_hash(form.password.data).decode("utf-8", "ignore")
        user = User(username = form.username.data, email = form.email.data, password = pw_hash)
        db.session.add(user)
        db.session.commit()
        #flash(form.name.data)
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            return redirect(url_for('home'))        
        else:
            return "wrong password"
    return render_template('login.html', form = form)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/")
def home():
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "tIS1YZZIEro0z5j190aXzw", "isbns": "9781632168146"})
    if res.status_code != 200:
        raise Exception("Error: API request unsuccessful.")
    return str(res.json())
    #return "Hello World"

@app.route("/place")
def place():
    res = requests.get("https://jsonplaceholder.typicode.com/todos/1")
    if res.status_code != 200:
        raise Exception("Error: API request unsuccessful.")
    return str(res.json())

#imports data from csv
# @app.route("/download")
# def download():
#     f = open("books.csv")
#     reader = csv.reader(f)
#     for isbn, title, author, year in reader:
#         book = Book(isbn=isbn, title=title, author=author, year=year)
#         db.session.add(book)
#     db.session.commit()
#     return "Hooray"