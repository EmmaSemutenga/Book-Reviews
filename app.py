#imports
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
import requests
import csv
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, BooleanField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, Length, Email, EqualTo, NumberRange
from flask_bcrypt import Bcrypt
from flask_login import UserMixin, LoginManager, login_user, current_user, logout_user, login_required

#configurations
app = Flask(__name__)
app.config['SECRET_KEY']="get yours"
POSTGRES = {
    'user': 'postgres',
    'pw': 'tunga',
    'db': 'bok',
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

#Loading user on the fly
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

#models
#User Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    #posts = db.relationship('Post', backref='author', lazy=True, cascade="all, delete-orphan")#this is a relationship not a column
    reviews = db.relationship('Review', backref='reviewer', lazy=True, cascade="all, delete-orphan")#this is a relationship not a column

#book model
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    isbn = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    #user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reviews = db.relationship('Review', backref='author', lazy=True, cascade="all, delete-orphan")#this is a relationship not a column

#review model
class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    comment = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
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
    rating = IntegerField('Rating', validators=[DataRequired(), NumberRange(min=1, max=5)])
    submit = SubmitField('Review')

class SearchForm(FlaskForm):
    search = StringField('ISBN, Title or Author', validators=[DataRequired(), Length(min=2, max=20)])
    submit = SubmitField('Search')

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
            return redirect(url_for('books'))        
        else:
            return "wrong password"
    return render_template('login.html', form = form)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route("/books", methods=['GET', 'POST'])
@login_required
def books():
    form = SearchForm()
    if form.validate_on_submit():
        search = form.search.data
        #books = select(Book).where((isbn == search) or (title == search) or (author == search))
        #books = Book.query.filter_by(isbn=search).all() or Book.query.filter_by(title=search).all() or Book.query.filter_by(author=search).all() or Book.query.filter_by(year=search).all()
        #books = Book.query.filter(Book.title.endswith(search)).all()
        #books = Book.query.filter(Book.title.contains(search)).all() or Book.query.filter(Book.isbn.contains(search)).all() or Book.query.filter(Book.author.contains(search)).all()
        #books = Book.query.filter((Book.isbn == search) | (Book.title == search) | (Book.author == search) | (Book.year == search))
        books = Book.query.filter((Book.isbn.contains(search)) | (Book.title.contains(search)) | (Book.author.contains(search)) | (Book.year.contains(search)))
        return render_template('books.html', books = books, form=form)
    books = Book.query.all()
    return render_template('books.html', books = books, form=form)

@app.route("/book/<int:book_id>", methods=['GET', 'POST'])
@login_required
def book(book_id):
    book = Book.query.filter_by(id=book_id).first()
    reviews = Review.query.filter_by(book_id=book_id).all()
    #goodreads website reviews
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "tIS1YZZIEro0z5j190aXzw", "isbns": book.isbn})
    if res.status_code != 200:
        raise Exception("Error: API request unsuccessful.")
    good_reviews = res.json()['books']
    #check if user has reviewed this book before
    user_review = Review.query.filter_by(reviewer = current_user, book_id=book_id).first()
    form = ReviewForm()
    #if user_review is None:
    if not user_review:
        if form.validate_on_submit():
            review = Review(comment = form.comment.data, rating = form.rating.data, book_id = book_id, reviewer = current_user )
            db.session.add(review)
            db.session.commit()
            return redirect(url_for('book', book_id=book_id))
    #return render_template('book.html', book = book,reviews = reviews)
    return render_template('book.html', book = book, form=form, reviews = reviews, user_review = user_review, good_reviews = good_reviews)

@app.route("/api/<isbn>")
def isbn_api(isbn):
    book = Book.query.filter_by(isbn=isbn).first()
    #average_score = accumulated number of ratings/review_count
    if book is None:
        return jsonify({"error" : "Invalid isbn"}), 422
    #only check for reviews if book exist
    reviews = book.reviews
    review_count = len(reviews)

    return jsonify({
        "title": book.title,
        "author": book.author,
        "year": book.year,
        "isbn": book.isbn,
        "review_count": review_count
    })
    

# @app.route("/")
# def home():
#     res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "tIS1YZZIEro0z5j190aXzw", "isbns": "9781632168146"})
#     if res.status_code != 200:
#         raise Exception("Error: API request unsuccessful.")
#     return str(res.json())
#     #return "Hello World"

# @app.route("/place")
# def place():
#     res = requests.get("https://jsonplaceholder.typicode.com/todos/1")
#     if res.status_code != 200:
#         raise Exception("Error: API request unsuccessful.")
#     return str(res.json())

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

# {
#     'books': [{
#         'id': 29207858, 
#         'isbn': '1632168146', 
#         'isbn13': '9781632168146', 
#         'ratings_count': 0, 
#         'reviews_count': 2, 
#         'text_reviews_count': 0, 
#         'work_ratings_count': 26, 
#         'work_reviews_count': 119, 
#         'work_text_reviews_count': 10, 
#         'average_rating': '4.04'
#         }]
# }