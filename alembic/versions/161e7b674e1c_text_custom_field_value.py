"""text custom field value

Revision ID: 161e7b674e1c
Revises: 2e3ca450412b
Create Date: 2015-03-06 16:32:43.526362

"""

# revision identifiers, used by Alembic.
revision = '161e7b674e1c'
down_revision = '2e3ca450412b'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('custom_field_value', 'value',
                    existing_type=sa.String(length=512),
                    type_=sa.Text(),
                    existing_nullable=False)


def downgrade():
    op.alter_column('custom_field_value', 'value',
                    existing_type=sa.Text(),
                    type_=sa.String(length=512),
                    existing_nullable=False)
