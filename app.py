from flask import Flask
from flask_migrate import Migrate
from models import db
from models.work import Work
from models.blog import BlogPost
from models.user import User
from routes import register_routes
from routes.blog import register_blog_routes
from routes.auth import register_auth_routes
from routes.admin import register_admin_routes
from routes.profile import register_profile_routes
from commands import create_admin_command
from auth.oauth import oauth_handler
from routes.forum import forum, init_forum_routes
from flask_login import LoginManager, current_user
from search import search

app = Flask(__name__)

# Load configuration
app.config.from_object('config.Config')
app.config.update(
    SQLALCHEMY_DATABASE_URI='sqlite:////Users/a86136/PycharmProjects/shakespeare_project/instance/corpus.db',
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SECRET_KEY='your-secret-key-here'
)

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
oauth_handler.init_app(app)

# Register routes
register_routes(app)
register_auth_routes(app)
register_blog_routes(app)
register_admin_routes(app)
register_profile_routes(app)
search.init_app(app)

# Register forum routes - fixed the double registration
forum_blueprint = init_forum_routes(app)
app.register_blueprint(forum_blueprint)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register commands
app.cli.add_command(create_admin_command)

# Add Content Security Policy (CSP) headers
@app.after_request
def set_csp_headers(response):
    response.headers['Content-Security-Policy'] = (
        "script-src 'self'; "
        "style-src 'self' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com;"
    )
    return response



if __name__ == "__main__":
    app.run(debug=True)
