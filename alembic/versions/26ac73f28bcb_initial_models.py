"""initial models

Revision ID: 26ac73f28bcb
Revises: None
Create Date: 2014-07-09 15:37:04.158690

"""

# revision identifiers, used by Alembic.
revision = '26ac73f28bcb'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'meeting_type',
        sa.Column('slug', sa.String(length=16), nullable=False),
        sa.Column('name', sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint('slug')
    )
    op.create_table(
        'user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('first_name', sa.String(length=32), nullable=False),
        sa.Column('last_name', sa.String(length=32), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('password', sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_table(
        'meeting',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=32), nullable=False),
        sa.Column('acronym', sa.String(length=16), nullable=False),
        sa.Column('meeting_type_id', sa.String(length=32), nullable=False),
        sa.Column('date_start', sa.DateTime(), nullable=False),
        sa.Column('date_end', sa.DateTime(), nullable=False),
        sa.Column('venue_address', sa.String(length=128), nullable=True),
        sa.Column('venue_city', sa.String(length=32), nullable=False),
        sa.Column('venue_country', sa.String(length=32), nullable=False),
        sa.Column('admin_name', sa.String(length=32), nullable=True),
        sa.Column('admin_email', sa.String(length=32), nullable=True),
        sa.Column('media_admin_name', sa.String(length=32), nullable=True),
        sa.Column('media_admin_email', sa.String(length=32), nullable=True),
        sa.Column('online_registration', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['meeting_type_id'], ['meeting_type.slug'], ),
        sa.PrimaryKeyConstraint('id')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('meeting')
    op.drop_table('user')
    op.drop_table('meeting_type')
    ### end Alembic commands ###
