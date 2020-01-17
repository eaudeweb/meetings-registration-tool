"""Add photo size column

Revision ID: a06a21bd4873
Revises: fd9fde81c629
Create Date: 2020-01-16 13:39:19.429664

"""

# revision identifiers, used by Alembic.
revision = 'a06a21bd4873'
down_revision = 'fd9fde81c629'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('custom_field', sa.Column('photo_size', sa.Unicode(255), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('custom_field', 'photo_size')
    # ### end Alembic commands ###