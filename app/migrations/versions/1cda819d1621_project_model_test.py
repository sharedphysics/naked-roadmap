"""Project model test

Revision ID: 1cda819d1621
Revises: 164f23bed3ad
Create Date: 2025-04-03 21:23:44.011879

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1cda819d1621'
down_revision = '164f23bed3ad'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('project',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=256), nullable=True),
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.Column('dri', sa.String(length=256), nullable=True),
    sa.Column('team', sa.String(length=256), nullable=True),
    sa.Column('context', sa.Text(), nullable=True),
    sa.Column('why', sa.Text(), nullable=True),
    sa.Column('requirements', sa.Text(), nullable=True),
    sa.Column('launch', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created', sa.DateTime(), nullable=False))
        batch_op.add_column(sa.Column('content', sa.TEXT(), nullable=False))
        batch_op.add_column(sa.Column('title', sa.TEXT(), nullable=False))
        batch_op.drop_index('ix_post_timestamp')
        batch_op.create_index(batch_op.f('ix_post_created'), ['created'], unique=False)
        batch_op.drop_column('body')
        batch_op.drop_column('timestamp')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.add_column(sa.Column('timestamp', sa.DATETIME(), nullable=False))
        batch_op.add_column(sa.Column('body', sa.VARCHAR(length=140), nullable=False))
        batch_op.drop_index(batch_op.f('ix_post_created'))
        batch_op.create_index('ix_post_timestamp', ['timestamp'], unique=False)
        batch_op.drop_column('title')
        batch_op.drop_column('content')
        batch_op.drop_column('created')

    op.drop_table('project')
    # ### end Alembic commands ###
