from flask import Flask, render_template, redirect, url_for, flash, request
import requests
import csv
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

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


#models
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    isbn = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    year = db.Column(db.String(100), nullable=False)

#routes

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