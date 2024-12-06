from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from models import db
from models.user import User
from models.forum import Category, Topic, Post, PostLike, TopicFollow, SavedPost
from forms.forum import TopicForm, PostForm, CategoryForm, EditTopicForm, EditPostForm
from datetime import datetime

forum = Blueprint('forum', __name__, url_prefix='/forum')


# We'll need to wrap the blueprint routes with the decorator after registration
def init_forum_routes(app):
    @forum.route('/category/new', methods=['GET', 'POST'])
    @app.login_required
    def new_category():
        # Check if user is admin
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            flash('Admin access required')
            return redirect(url_for('forum.index'))

        form = CategoryForm()
        if form.validate_on_submit():
            category = Category(
                name=form.name.data,
                description=form.description.data
            )
            db.session.add(category)
            db.session.commit()
            flash('Category created successfully.')
            return redirect(url_for('forum.index'))

        return render_template('forum/new_category.html', form=form)

    @forum.route('/new-topic', methods=['GET', 'POST'])
    @app.login_required
    def new_topic():
        form = TopicForm()
        if form.validate_on_submit():
            user = User.query.get(session['user_id'])
            topic = Topic(
                title=form.title.data,
                content=form.content.data,
                category_id=form.category.data,
                user=user
            )
            db.session.add(topic)
            db.session.commit()
            flash('Topic created successfully.')
            return redirect(url_for('forum.topic', topic_id=topic.id))
        return render_template('forum/new_topic.html', form=form)

    @forum.route('/like/<int:post_id>', methods=['POST'])
    @app.login_required
    def like(post_id):
        post = Post.query.get_or_404(post_id)
        user = User.query.get(session['user_id'])
        like = PostLike.query.filter_by(user=user, post=post).first()
        if not like:
            like = PostLike(user=user, post=post)
            db.session.add(like)
            db.session.commit()
        return redirect(url_for('forum.topic', topic_id=post.topic_id, page=request.args.get('page', 1, type=int)))

    @forum.route('/follow/<int:topic_id>', methods=['POST'])
    @app.login_required
    def follow(topic_id):
        topic = Topic.query.get_or_404(topic_id)
        user = User.query.get(session['user_id'])
        follow = TopicFollow.query.filter_by(user=user, topic=topic).first()
        if not follow:
            follow = TopicFollow(user=user, topic=topic)
            db.session.add(follow)
            db.session.commit()
        return redirect(url_for('forum.topic', topic_id=topic.id))

    # Routes that don't need login_required
    @forum.route('/')
    def index():
        categories = Category.query.all()
        for category in categories:
            # Get topic count for this category
            category.topic_count = Topic.query.filter_by(category_id=category.id).count()
            # Get latest topic for this category
            category.latest_topic = Topic.query.filter_by(category_id=category.id).order_by(
                Topic.created_at.desc()).first()
        return render_template('forum/index.html', categories=categories)

    @forum.route('/category/<int:category_id>')
    def category(category_id):
        category = Category.query.get_or_404(category_id)
        topics = Topic.query.filter_by(category_id=category_id).order_by(Topic.updated_at.desc()).paginate(per_page=20)
        return render_template('forum/category.html', category=category, topics=topics)

    @forum.route('/topic/<int:topic_id>', methods=['GET', 'POST'])
    def topic(topic_id):
        topic = Topic.query.get_or_404(topic_id)
        form = PostForm()

        if request.method == 'POST':
            if 'user_id' not in session:
                flash('Please login to post a reply')
                return redirect(url_for('login'))

            if form.validate_on_submit():
                user = User.query.get(session['user_id'])
                post = Post(content=form.content.data, topic=topic, user=user)
                db.session.add(post)
                db.session.commit()
                flash('Your reply has been posted.')
                return redirect(url_for('forum.topic', topic_id=topic.id, page=-1))

        page = request.args.get('page', 1, type=int)
        if page == -1:
            page = (topic.posts.count() - 1) // 20 + 1
        posts = topic.posts.order_by(Post.created_at.asc()).paginate(page=page, per_page=20)
        return render_template('forum/topic.html', topic=topic, posts=posts, form=form)

    @forum.route('/topic/<int:topic_id>/edit', methods=['GET', 'POST'])
    @app.login_required
    def edit_topic(topic_id):
        topic = Topic.query.get_or_404(topic_id)
        user = User.query.get(session['user_id'])

        # Check if user is author or admin
        if user.id != topic.user_id and not user.is_admin:
            flash('You do not have permission to edit this topic')
            return redirect(url_for('forum.topic', topic_id=topic.id))

        form = EditTopicForm()
        if request.method == 'GET':
            form.title.data = topic.title
            form.content.data = topic.content

        if form.validate_on_submit():
            topic.title = form.title.data
            topic.content = form.content.data
            topic.updated_at = datetime.utcnow()
            db.session.commit()
            flash('Topic updated successfully')
            return redirect(url_for('forum.topic', topic_id=topic.id))

        return render_template('forum/edit_topic.html', form=form, topic=topic)

    @forum.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
    @app.login_required
    def edit_post(post_id):
        post = Post.query.get_or_404(post_id)
        user = User.query.get(session['user_id'])

        # Check if user is author or admin
        if user.id != post.user_id and not user.is_admin:
            flash('You do not have permission to edit this post')
            return redirect(url_for('forum.topic', topic_id=post.topic_id))

        form = EditPostForm()
        if request.method == 'GET':
            form.content.data = post.content

        if form.validate_on_submit():
            post.content = form.content.data
            post.updated_at = datetime.utcnow()
            db.session.commit()
            flash('Post updated successfully')
            return redirect(url_for('forum.topic', topic_id=post.topic_id))

        return render_template('forum/edit_post.html', form=form, post=post)

    @forum.route('/post/<int:post_id>/reply', methods=['POST'])
    @app.login_required
    def reply_to_post(post_id):
        parent_post = Post.query.get_or_404(post_id)
        form = PostForm()

        if form.validate_on_submit():
            post = Post(
                content=form.content.data,
                topic_id=parent_post.topic_id,
                user_id=session['user_id'],
                parent_id=parent_post.id
            )
            db.session.add(post)
            db.session.commit()
            flash('Reply posted successfully')

        return redirect(url_for('forum.topic', topic_id=parent_post.topic_id))

    @forum.route('/post/<int:post_id>/save', methods=['POST'])
    @app.login_required
    def save_post(post_id):
        post = Post.query.get_or_404(post_id)
        user_id = session['user_id']

        saved = SavedPost.query.filter_by(user_id=user_id, post_id=post_id).first()
        if saved:
            db.session.delete(saved)
            message = 'Post removed from saved items'
        else:
            saved = SavedPost(user_id=user_id, post_id=post_id)
            db.session.add(saved)
            message = 'Post saved successfully'

        db.session.commit()
        return jsonify({'message': message}), 200

    @forum.context_processor
    def utility_processor():
        return dict(get_user=lambda id: User.query.get(id))

    return forum