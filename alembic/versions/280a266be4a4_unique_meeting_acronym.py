"""unique meeting acronym

Revision ID: 280a266be4a4
Revises: 273a70e8bc07
Create Date: 2015-01-15 15:04:45.775448

"""

# revision identifiers, used by Alembic.
revision = '280a266be4a4'
down_revision = '273a70e8bc07'

from alembic import op


def upgrade():
    op.create_unique_constraint('uq_meeting_acronym', 'meeting', ['acronym'])


def downgrade():
    op.drop_constraint('uq_meeting_acronym', 'meeting')
