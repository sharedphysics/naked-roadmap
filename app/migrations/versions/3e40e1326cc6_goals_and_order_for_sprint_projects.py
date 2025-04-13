"""Goals and order for sprint projects

Revision ID: 3e40e1326cc6
Revises: 48cd7a2f6d3b
Create Date: 2025-04-13 13:23:28.857798

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3e40e1326cc6'
down_revision = '48cd7a2f6d3b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('sprint_project_map', schema=None) as batch_op:
        batch_op.add_column(sa.Column('order', sa.Integer(), autoincrement=True, nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('sprint_project_map', schema=None) as batch_op:
        batch_op.drop_column('order')

    # ### end Alembic commands ###
