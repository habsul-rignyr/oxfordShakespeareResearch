"""Add nested replies and saved posts

Revision ID: 9c48e02f534a
Revises: 1d4badcdf453
Create Date: 2024-12-06 13:23:24.917976

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9c48e02f534a'
down_revision = '1d4badcdf453'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.add_column(sa.Column('parent_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_post_parent', 'post', ['parent_id'], ['id'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.drop_constraint('fk_post_parent', type_='foreignkey')
        batch_op.drop_column('parent_id')

    # ### end Alembic commands ###