"""add working language

Revision ID: 4533d247270e
Revises: 7835855bd3
Create Date: 2014-08-07 11:30:31.755134

"""

# revision identifiers, used by Alembic.
revision = '4533d247270e'
down_revision = '7835855bd3'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('participant', sa.Column('language',
                                           sa.String(length=255),
                                           nullable=False))


def downgrade():
    op.drop_column('participant', 'language')
