import click
from flask.cli import with_appcontext
from models import db
from models.user import User

@click.command('create-admin')
@click.argument('username')
@click.argument('email')
@click.argument('password')
@with_appcontext
def create_admin_command(username, email, password):
    """Create an admin user"""
    user = User(
        username=username,
        email=email,
        is_admin=True,
        name=username  # Can be updated later
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f'Created admin user: {username}')