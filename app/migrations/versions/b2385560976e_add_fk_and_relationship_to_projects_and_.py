"""Add fk and relationship to projects and objectives

Revision ID: b2385560976e
Revises: d152f859699e
Create Date: 2025-04-18 21:10:25.343359

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2385560976e'
down_revision = 'd152f859699e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.add_column(sa.Column('objective_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(None, 'goal', ['objective_id'], ['id'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('objective_id')

    # ### end Alembic commands ###
