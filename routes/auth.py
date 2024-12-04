from flask import render_template, redirect, url_for, request, flash, session
from models import db
from models.user import User
from functools import wraps


def register_auth_routes(app):
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']

            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                session['user_id'] = user.id
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

            user = User(
                username=username,
                email=email,
                name=name
            )
            user.set_password(password)

            db.session.add(user)
            db.session.commit()

            session['user_id'] = user.id
            return redirect(url_for('profile'))

        return render_template('auth/register.html')

    @app.route('/logout')
    def logout():
        session.pop('user_id', None)
        return redirect(url_for('home'))

    # Add login_required decorator for protected routes
    def login_required(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            return view_func(*args, **kwargs)

        return wrapped_view

    # Add admin_required decorator for admin routes
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

    # Make decorators available to other routes
    app.login_required = login_required
    app.admin_required = admin_required


