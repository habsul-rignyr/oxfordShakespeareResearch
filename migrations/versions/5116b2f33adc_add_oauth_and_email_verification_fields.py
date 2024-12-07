"""Add oauth and email verification fields

Revision ID: 5116b2f33adc
Revises: 079d1d6cf1ae
Create Date: 2024-12-05 19:55:04.231197

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5116b2f33adc'
down_revision = '079d1d6cf1ae'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email_verified', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('verification_token', sa.String(length=100), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('verification_token')
        batch_op.drop_column('email_verified')

    # ### end Alembic commands ###
