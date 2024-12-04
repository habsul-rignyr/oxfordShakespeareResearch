from flask import render_template, redirect, url_for, request, flash, session
from models import db
from models.blog import BlogPost
from slugify import slugify
from datetime import datetime
from models.user import User


def register_admin_routes(app):
    @app.route('/admin/blog/new', methods=['GET', 'POST'])
    @app.admin_required
    def admin_new_post():
        if request.method == 'POST':
            title = request.form['title']
            content = request.form['content']
            slug = slugify(title)

            # Get current user
            user = User.query.get(session['user_id'])

            post = BlogPost(
                title=title,
                slug=slug,
                content=content,
                published=True,
                author_id=user.id
            )

            db.session.add(post)
            db.session.commit()

            return redirect(url_for('blog_post', slug=slug))

        return render_template('admin/new_post.html')

    @app.route('/admin/blog')
    @app.admin_required
    def admin_blog():
        user = User.query.get(session['user_id'])
        # If super admin, show all posts, otherwise show only user's posts
        if user.is_admin:
            posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
        else:
            posts = BlogPost.query.filter_by(author_id=user.id).order_by(BlogPost.created_at.desc()).all()
        return render_template('admin/blog_list.html', posts=posts)

    @app.route('/admin/blog/<int:post_id>/edit', methods=['GET', 'POST'])
    @app.admin_required
    def admin_edit_post(post_id):
        post = BlogPost.query.get_or_404(post_id)
        user = User.query.get(session['user_id'])

        # Check if user is either super admin or post author
        if not user.is_admin and post.author_id != user.id:
            flash('You do not have permission to edit this post')
            return redirect(url_for('admin_blog'))

        if request.method == 'POST':
            post.title = request.form['title']
            post.content = request.form['content']
            post.slug = slugify(post.title)
            post.updated_at = datetime.utcnow()

            db.session.commit()
            return redirect(url_for('blog_post', slug=post.slug))

        return render_template('admin/edit_post.html', post=post)