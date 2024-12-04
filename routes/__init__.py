from .main import register_routes
from .blog import register_blog_routes

# This allows importing register_routes directly from routes package
__all__ = ['register_routes', 'register_blog_routes']