# auth/oauth.py
from flask import url_for, session, current_app
from authlib.integrations.flask_client import OAuth
import string
import random


def generate_random_string():
    return "".join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=32))


class OAuthHandler:
    def __init__(self, app=None):
        self.oauth = OAuth()
        if app:
            self.init_app(app)

    def init_app(self, app):
        self.oauth.init_app(app)

        # Register Twitter with PKCE
        self.oauth.register(
            name='twitter',
            client_id=app.config['TWITTER_CLIENT_ID'],
            client_secret=app.config['TWITTER_CLIENT_SECRET'],
            access_token_url='https://api.twitter.com/2/oauth2/token',
            authorize_url='https://twitter.com/i/oauth2/authorize',
            api_base_url='https://api.twitter.com/2/',
            client_kwargs={
                'scope': 'tweet.read users.read',
                'code_challenge_method': 'plain',
                'code_challenge': generate_random_string()
            }
        )

        # Keep Google as is
        self.oauth.register(
            name='google',
            client_id=app.config['GOOGLE_CLIENT_ID'],
            client_secret=app.config['GOOGLE_CLIENT_SECRET'],
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'},
        )

    def get_provider(self, name):
        if name == 'twitter':
            # Store the code challenge for later verification
            session['twitter_code_challenge'] = self.oauth.twitter.client_kwargs['code_challenge']
            session['twitter_code_challenge_method'] = 'plain'
        return self.oauth.create_client(name)


# Create the instance
oauth_handler = OAuthHandler()