"""badge header meeting

Revision ID: 16f621b20f25
Revises: 2f4220e008ea
Create Date: 2014-08-21 17:52:14.665931

"""

# revision identifiers, used by Alembic.
revision = '16f621b20f25'
down_revision = '3cbf4b74f3ad'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('meeting', sa.Column('badge_header_id', sa.Integer(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('meeting', 'badge_header_id')
    ### end Alembic commands ###
