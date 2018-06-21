"""add index on custom_field_value

Revision ID: fd9fde81c629
Revises: 31eaa9c4237d
Create Date: 2018-06-21 11:34:35.453146

"""

# revision identifiers, used by Alembic.
revision = 'fd9fde81c629'
down_revision = '31eaa9c4237d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_index(op.f('ix_custom_field_value_participant_id'),
                    'custom_field_value', ['participant_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_custom_field_value_participant_id'),
                  table_name='custom_field_value')
