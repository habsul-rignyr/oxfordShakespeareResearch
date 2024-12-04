from flask import render_template, redirect, url_for, request, flash, session
from werkzeug.utils import secure_filename
import os
from models import db
from models.user import User


def register_profile_routes(app):
    UPLOAD_FOLDER = 'static/uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    @app.route('/profile')
    def profile():
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        return render_template('profile/view.html', user=user, is_owner=True)

    @app.route('/profile/<username>')
    def view_profile(username):
        user = User.query.filter_by(username=username).first_or_404()
        is_owner = 'user_id' in session and session['user_id'] == user.id
        return render_template('profile/view.html', user=user, is_owner=is_owner)

    @app.route('/profile/edit', methods=['GET', 'POST'])
    @app.login_required
    def edit_profile():
        user = User.query.get(session['user_id'])

        if request.method == 'POST':
            user.name = request.form['name']
            user.bio = request.form['bio']
            user.twitter = request.form['twitter']
            user.github = request.form['github']
            user.website = request.form['website']

            if 'avatar' in request.files:
                file = request.files['avatar']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(filepath)
                    user.avatar = url_for('static', filename=f'uploads/{filename}')

            db.session.commit()
            return redirect(url_for('profile'))

        return render_template('profile/edit.html', user=user)