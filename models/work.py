from models import db  # Import db from models/__init__.py

class Work(db.Model):
    __tablename__ = 'work'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    genre = db.Column(db.String(100), nullable=False)
    publication_year = db.Column(db.Integer)
    edition = db.Column(db.String(100))
    attribution = db.Column(db.String(100))
    file_path = db.Column(db.String(500), nullable=False)  # Increased length for deep paths
    format = db.Column(db.String(10), nullable=False)
    notes = db.Column(db.Text)

    def __repr__(self):
        return f"<Work(title={self.title}, author={self.author}, genre={self.genre})>"
