"""default custom fields

Revision ID: 2e3ca450412b
Revises: 41cc4d896b41
Create Date: 2015-02-20 12:19:29.526425

"""

# revision identifiers, used by Alembic.
revision = '2e3ca450412b'
down_revision = '41cc4d896b41'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('meeting_type_custom_field',
    sa.Column('meeting_type_slug', sa.String(length=16), nullable=True),
    sa.Column('custom_field_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['custom_field_id'], ['custom_field.id'], ),
    sa.ForeignKeyConstraint(['meeting_type_slug'], ['meeting_type.slug'], )
    )


def downgrade():
    op.drop_constraint('fk_media_photo_field', 'meeting', type_='foreignkey')
    op.drop_constraint('fk_photo_field', 'meeting', type_='foreignkey')
    op.drop_table('meeting_type_custom_field')
