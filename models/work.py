# models/work.py
from models import db


class Work(db.Model):
    __tablename__ = 'work'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    author = db.Column(db.String(200), nullable=True)
    genre = db.Column(db.String(100), nullable=True)
    publication_year = db.Column(db.Integer)
    edition = db.Column(db.String(100))
    attribution = db.Column(db.String(100))  # Keep this for now

    # New EEBO-specific fields
    tcp_id = db.Column(db.String(20), index=True)  # EEBO TCP ID
    eebo_id = db.Column(db.String(20))  # Original EEBO citation ID
    vid = db.Column(db.String(20))  # Volume ID
    source_library = db.Column(db.String(200))  # Original library source
    language = db.Column(db.String(50))  # Primary language
    collection = db.Column(db.String(50))  # e.g., 'TCP Phase I', 'Shakespeare First Folio'

    file_path = db.Column(db.String(500), nullable=False)
    format = db.Column(db.String(10), nullable=False)
    notes = db.Column(db.Text)

    __table_args__ = (
        db.Index('idx_tcp_id', 'tcp_id'),
        db.Index('idx_title', 'title'),
    )

    def __repr__(self):
        return f"<Work(title={self.title}, author={self.author}, tcp_id={self.tcp_id})>"