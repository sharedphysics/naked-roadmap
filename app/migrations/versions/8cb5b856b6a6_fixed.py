"""Fixed

Revision ID: 8cb5b856b6a6
Revises: 7c2fb87fefe6
Create Date: 2025-04-13 21:59:27.621157

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8cb5b856b6a6'
down_revision = '7c2fb87fefe6'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.add_column(sa.Column('type', sa.TEXT(), nullable=True))

    with op.batch_alter_table('sprint_project_map', schema=None) as batch_op:
        batch_op.add_column(sa.Column('critical', sa.Boolean(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('sprint_project_map', schema=None) as batch_op:
        batch_op.drop_column('critical')

    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.drop_column('type')

    # ### end Alembic commands ###
