from flask import Flask
from flask_migrate import Migrate
from models import db
from models.work import Work
from models.blog import BlogPost
from models.user import User
from routes import register_routes
from routes.blog import register_blog_routes
from routes.auth import register_auth_routes  # Add this import
from routes.admin import register_admin_routes
from commands import create_admin_command
from routes.profile import register_profile_routes

app = Flask(__name__)

# Configure the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/a86136/PycharmProjects/shakespeare_project/instance/corpus.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Add this for sessions

# Initialize the database and migrations
db.init_app(app)
migrate = Migrate(app, db)

# Register routes - note the order!
register_routes(app)
register_auth_routes(app)  # Register auth first to provide decorators
register_blog_routes(app)
register_admin_routes(app)
register_profile_routes(app)

# Register commands
app.cli.add_command(create_admin_command)

if __name__ == "__main__":
    app.run(debug=True)