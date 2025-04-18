"""Projects

Revision ID: fa5b71a880a4
Revises: 1cda819d1621
Create Date: 2025-04-04 13:45:06.315093

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fa5b71a880a4'
down_revision = '1cda819d1621'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.alter_column('name',
               existing_type=sa.VARCHAR(length=256),
               type_=sa.TEXT(),
               nullable=False)
        batch_op.alter_column('created',
               existing_type=sa.DATETIME(),
               nullable=False)
        batch_op.alter_column('dri',
               existing_type=sa.VARCHAR(length=256),
               type_=sa.TEXT(),
               nullable=False)
        batch_op.alter_column('team',
               existing_type=sa.VARCHAR(length=256),
               type_=sa.TEXT(),
               nullable=False)
        batch_op.alter_column('context',
               existing_type=sa.TEXT(),
               nullable=False)
        batch_op.alter_column('why',
               existing_type=sa.TEXT(),
               nullable=False)
        batch_op.alter_column('requirements',
               existing_type=sa.TEXT(),
               nullable=False)
        batch_op.alter_column('launch',
               existing_type=sa.TEXT(),
               nullable=False)
        batch_op.create_index(batch_op.f('ix_project_created'), ['created'], unique=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_project_created'))
        batch_op.alter_column('launch',
               existing_type=sa.TEXT(),
               nullable=True)
        batch_op.alter_column('requirements',
               existing_type=sa.TEXT(),
               nullable=True)
        batch_op.alter_column('why',
               existing_type=sa.TEXT(),
               nullable=True)
        batch_op.alter_column('context',
               existing_type=sa.TEXT(),
               nullable=True)
        batch_op.alter_column('team',
               existing_type=sa.TEXT(),
               type_=sa.VARCHAR(length=256),
               nullable=True)
        batch_op.alter_column('dri',
               existing_type=sa.TEXT(),
               type_=sa.VARCHAR(length=256),
               nullable=True)
        batch_op.alter_column('created',
               existing_type=sa.DATETIME(),
               nullable=True)
        batch_op.alter_column('name',
               existing_type=sa.TEXT(),
               type_=sa.VARCHAR(length=256),
               nullable=True)

    # ### end Alembic commands ###
