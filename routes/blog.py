from flask import render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
import os
from models import db
from models.blog import BlogPost, Comment
from models.user import User
from slugify import slugify

HEADER_IMAGE_FOLDER = 'static/header_images'


def register_blog_routes(app):
    if not os.path.exists(HEADER_IMAGE_FOLDER):
        os.makedirs(HEADER_IMAGE_FOLDER)

    @app.route('/blog')
    def blog_index():
        posts = BlogPost.query.filter_by(published=True).order_by(BlogPost.created_at.desc()).all()
        return render_template('blog/index.html', posts=posts)

    @app.route('/blog/new', methods=['GET', 'POST'])
    @app.admin_required
    def new_post():
        if request.method == 'POST':
            title = request.form['title']
            content = request.form['content']
            slug = slugify(title)

            post = BlogPost(
                title=title,
                slug=slug,
                content=content,
                published=True,
                author_id=session['user_id']
            )

            if 'header_image' in request.files:
                header_image = request.files['header_image']
                if header_image.filename:
                    filename = secure_filename(header_image.filename)
                    filepath = os.path.join(HEADER_IMAGE_FOLDER, filename)
                    header_image.save(filepath)
                    post.header_image = filename

            db.session.add(post)
            db.session.commit()
            return redirect(url_for('blog_post', slug=slug))

        return render_template('blog/blog_editor.html')

    @app.route('/blog/<slug>')
    def blog_post(slug):
        post = BlogPost.query.filter_by(slug=slug, published=True).first_or_404()
        # Get only top-level comments
        comments = Comment.query.filter_by(post_id=post.id, parent_id=None).order_by(Comment.created_at.desc()).all()
        return render_template('blog/post.html', post=post, comments=comments)

    @app.route('/blog/<slug>/comment', methods=['POST'])
    @app.login_required
    def new_comment(slug):
        post = BlogPost.query.filter_by(slug=slug).first_or_404()
        content = request.form['content']
        parent_id = request.form.get('parent_id')

        comment = Comment(
            content=content,
            post_id=post.id,
            author_id=session['user_id'],
            parent_id=parent_id if parent_id else None
        )

        db.session.add(comment)
        db.session.commit()
        return redirect(url_for('blog_post', slug=slug))

    def get_user(user_id):
        return User.query.get(user_id)

    app.jinja_env.globals.update(get_user=get_user)

    @app.template_filter('format_date')
    def format_date(date):
        return date.strftime('%B %d, %Y')