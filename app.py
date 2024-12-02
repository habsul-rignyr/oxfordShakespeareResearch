from flask import Flask, render_template
from models import db
from models.work import Work

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///corpus.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.route('/')
def home():
    return render_template("home.html")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # This creates the tables if they don't already exist
    app.run(debug=True)