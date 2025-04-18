"""Requests table initial addition

Revision ID: 2a30658546b8
Revises: fa5b71a880a4
Create Date: 2025-04-04 21:29:15.347582

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2a30658546b8'
down_revision = 'fa5b71a880a4'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('request',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created', sa.DateTime(), nullable=False),
    sa.Column('title', sa.TEXT(), nullable=False),
    sa.Column('details', sa.TEXT(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('request', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_request_created'), ['created'], unique=False)
        batch_op.create_index(batch_op.f('ix_request_user_id'), ['user_id'], unique=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('request', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_request_user_id'))
        batch_op.drop_index(batch_op.f('ix_request_created'))

    op.drop_table('request')
    # ### end Alembic commands ###
