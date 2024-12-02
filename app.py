from flask import Flask, render_template, request
from models import db
from models.work import Work
from normalization import normalize_text  # Import normalization

import os
from rapidfuzz import process, fuzz

app = Flask(__name__)

# Configure the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/a86136/PycharmProjects/shakespeare_project/instance/corpus.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db.init_app(app)

# Preload titles for fuzzy searching
def preload_titles():
    works = Work.query.all()
    return {normalize_text(work.title): work for work in works}

title_index = {}

@app.route('/')
def home():
    return render_template("home.html")

@app.route('/search')
def search():
    query = request.args.get('query', '').strip()
    results = []

    if query:
        normalized_query = normalize_text(query)
        matched_titles = process.extract(
            normalized_query, title_index.keys(), limit=10, scorer=fuzz.ratio
        )
        results = [title_index[match[0]] for match in matched_titles if match[1] > 50]

    return render_template("search.html", query=query, results=results)

if __name__ == "__main__":
    with app.app_context():
        title_index = preload_titles()
    app.run(debug=True)
