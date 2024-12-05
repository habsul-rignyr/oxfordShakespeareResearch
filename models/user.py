from models import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(100))
    bio = db.Column(db.Text)
    avatar = db.Column(db.String(200))
    twitter = db.Column(db.String(100))
    github = db.Column(db.String(100))
    website = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # OAuth fields
    oauth_provider = db.Column(db.String(20))
    oauth_id = db.Column(db.String(100))
    oauth_username = db.Column(db.String(100))
    oauth_avatar = db.Column(db.String(200))
    email_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100))

    # Relationships
    blog_posts = db.relationship('BlogPost', backref='author', lazy=True)
    forum_topics = db.relationship('Topic', backref='user', lazy='dynamic')
    forum_posts = db.relationship('Post', backref='user', lazy='dynamic')
    likes = db.relationship('PostLike', backref='user', lazy='dynamic')
    followed_topics = db.relationship('TopicFollow', backref='user', lazy='dynamic')

    __table_args__ = (
        db.UniqueConstraint('oauth_provider', 'oauth_id', name='unique_oauth_user'),
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'