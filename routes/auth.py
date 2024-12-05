from flask import render_template, redirect, url_for, request, flash, session
from models import db
from models.user import User
from functools import wraps
from auth.oauth import oauth_handler, generate_random_string
import base64
import requests


def handle_oauth_user(user_info):
    # Check for existing OAuth user
    user = User.query.filter_by(
        oauth_provider=user_info['provider'],
        oauth_id=user_info['id']
    ).first()

    if user:
        return user

    # Check for email match (only for Google, since Twitter doesn't provide email)
    if user_info['email'] and user_info['provider'] == 'google':
        existing_user = User.query.filter_by(email=user_info['email']).first()
        if existing_user:
            session['pending_oauth'] = {
                'provider': user_info['provider'],
                'id': user_info['id'],
                'username': user_info['username'],
                'avatar': user_info['avatar']
            }
            return None

    # Create new user
    username = user_info['username']
    base_username = username
    counter = 1
    while User.query.filter_by(username=username).first():
        username = f"{base_username}{counter}"
        counter += 1

    user = User(
        username=username,
        email=user_info['email'] if user_info['email'] else None,
        oauth_provider=user_info['provider'],
        oauth_id=user_info['id'],
        oauth_username=user_info['username'],
        oauth_avatar=user_info['avatar'],
        email_verified=bool(user_info['email'])
    )
    db.session.add(user)
    db.session.commit()
    return user


def register_auth_routes(app):
    def login_required(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            return view_func(*args, **kwargs)

        return wrapped_view

    def admin_required(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            user = User.query.get(session['user_id'])
            if not user or not user.is_admin:
                flash('Admin access required')
                return redirect(url_for('home'))
            return view_func(*args, **kwargs)

        return wrapped_view

    app.login_required = login_required
    app.admin_required = admin_required

    @app.route('/test-twitter')
    def test_twitter_auth():
        from urllib.parse import quote
        code_challenge = session.get('twitter_code_challenge', generate_random_string())
        session['twitter_code_challenge'] = code_challenge

        callback_uri = url_for('oauth_callback', provider='twitter', _external=True)
        auth_url = (
            'https://twitter.com/i/oauth2/authorize'
            '?response_type=code'
            f'&client_id={app.config["TWITTER_CLIENT_ID"]}'
            f'&redirect_uri={quote(callback_uri)}'
            '&scope=tweet.read+users.read'
            f'&state={generate_random_string()}'
            f'&code_challenge={code_challenge}'
            '&code_challenge_method=plain'
            '&prompt=select_account'  # Add this line
        )
        return redirect(auth_url)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                session['user_id'] = user.id
                if 'pending_oauth' in session:
                    return redirect(url_for('link_oauth'))
                return redirect(url_for('home'))
            flash('Invalid username or password')
            return redirect(url_for('login'))
        return render_template('auth/login.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            name = request.form.get('name', username)

            if User.query.filter_by(username=username).first():
                flash('Username already exists')
                return redirect(url_for('register'))
            if User.query.filter_by(email=email).first():
                flash('Email already registered')
                return redirect(url_for('register'))

            user = User(username=username, email=email, name=name)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            session['user_id'] = user.id
            return redirect(url_for('profile'))
        return render_template('auth/register.html')

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('home'))

    @app.route('/cancel-oauth-link')
    def cancel_oauth_link():
        if 'pending_oauth' in session:
            session.pop('pending_oauth')
        return redirect(url_for('login'))

    @app.route('/login/<provider>')
    def oauth_login(provider):
        if provider == 'twitter':
            return redirect(url_for('test_twitter_auth'))

        if provider not in ['google', 'twitter']:
            flash('Invalid OAuth provider')
            return redirect(url_for('login'))

        client = oauth_handler.get_provider(provider)
        redirect_uri = url_for('oauth_callback', provider=provider, _external=True)
        return client.authorize_redirect(redirect_uri)

    @app.route('/login/<provider>/callback')
    def oauth_callback(provider):
        try:
            if provider == 'twitter':
                code = request.args.get('code')

                # Create basic auth header from client id and secret
                message = f"{app.config['TWITTER_CLIENT_ID']}:{app.config['TWITTER_CLIENT_SECRET']}"
                base64_auth = base64.b64encode(message.encode('ascii')).decode('ascii')

                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Authorization': f'Basic {base64_auth}'
                }

                data = {
                    'code': code,
                    'grant_type': 'authorization_code',
                    'redirect_uri': url_for('oauth_callback', provider='twitter', _external=True),
                    'code_verifier': session['twitter_code_challenge']
                }

                # Get the access token
                token_response = requests.post(
                    'https://api.twitter.com/2/oauth2/token',
                    headers=headers,
                    data=data
                )

                if token_response.status_code != 200:
                    raise Exception(f"Token fetch failed: {token_response.text}")

                token = token_response.json()

                # Get user info using the access token
                headers = {"Authorization": f"Bearer {token['access_token']}"}
                user_response = requests.get(
                    'https://api.twitter.com/2/users/me?user.fields=profile_image_url',
                    headers=headers
                )

                if user_response.status_code != 200:
                    raise Exception(f"User info fetch failed: {user_response.text}")

                resp = user_response.json()

                user_info = {
                    'provider': 'twitter',
                    'id': resp['data']['id'],
                    'username': resp['data']['username'],
                    'email': None,
                    'avatar': resp['data'].get('profile_image_url', '')
                }

            else:  # Google
                client = oauth_handler.get_provider(provider)
                token = client.authorize_access_token()
                resp = client.get('https://www.googleapis.com/oauth2/v3/userinfo').json()
                user_info = {
                    'provider': 'google',
                    'id': resp['sub'],
                    'username': resp['email'].split('@')[0],
                    'email': resp['email'],
                    'avatar': resp.get('picture', '')
                }

            user = handle_oauth_user(user_info)
            if user is None:
                flash('An account with this email already exists. Please login to link accounts.')
                return redirect(url_for('login'))

            session['user_id'] = user.id

            # If Twitter user with no email, redirect to add email
            if provider == 'twitter' and not user.email:
                flash('Please add an email address to your account.')
                return redirect(url_for('add_email'))

            return redirect(url_for('home'))

        except Exception as e:
            flash(f'OAuth login failed: {str(e)}')
            return redirect(url_for('login'))

    @app.route('/link-oauth', methods=['GET', 'POST'])
    @login_required
    def link_oauth():
        if 'pending_oauth' not in session:
            flash('No pending OAuth link request')
            return redirect(url_for('profile'))

        if request.method == 'POST':
            user = User.query.get(session['user_id'])
            oauth_data = session.pop('pending_oauth')

            user.oauth_provider = oauth_data['provider']
            user.oauth_id = oauth_data['id']
            user.oauth_username = oauth_data['username']
            user.oauth_avatar = oauth_data['avatar']

            db.session.commit()
            flash('Account successfully linked!')
            return redirect(url_for('profile'))

        return render_template('auth/link_oauth.html')

    @app.route('/add-email', methods=['GET', 'POST'])
    @login_required
    def add_email():
        if request.method == 'POST':
            email = request.form.get('email')
            if not email:
                flash('Email is required')
                return redirect(url_for('add_email'))

            if User.query.filter_by(email=email).first():
                flash('Email already registered')
                return redirect(url_for('add_email'))

            user = User.query.get(session['user_id'])
            user.email = email
            user.email_verified = False
            db.session.commit()

            flash('Email added successfully. Verification required.')
            return redirect(url_for('profile'))

        return render_template('auth/add_email.html')

    return app