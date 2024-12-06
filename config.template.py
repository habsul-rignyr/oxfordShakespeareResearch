class Config:
    # Database
    SQLALCHEMY_DATABASE_URI = 'sqlite:///path/to/your/database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Security
    SECRET_KEY = 'your-secret-key-here'

    # OAuth Credentials
    GOOGLE_CLIENT_ID = 'your-google-client-id'
    GOOGLE_CLIENT_SECRET = 'your-google-client-secret'

    TWITTER_CLIENT_ID = 'your-twitter-client-id'
    TWITTER_CLIENT_SECRET = 'your-twitter-client-secret'