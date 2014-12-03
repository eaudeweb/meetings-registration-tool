"""Add meeting_type table.

Revision ID: 42fad7c5fc31
Revises: 49f5e88ffa53
Create Date: 2014-12-08 16:54:33.337387

"""

# revision identifiers, used by Alembic.
revision = '42fad7c5fc31'
down_revision = '49f5e88ffa53'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'meeting_type',
        sa.Column('slug', sa.String(length=16), nullable=False),
        sa.Column('label', sa.String(length=128), nullable=False),
        sa.Column('default', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('slug'),
        sa.UniqueConstraint('slug')
    )
    op.alter_column(u'meeting', 'meeting_type',
                    existing_type=sa.VARCHAR(length=3),
                    type_=sa.String(length=16),
                    existing_nullable=False)
    op.alter_column(u'phrase_default', 'meeting_type',
                    existing_type=sa.VARCHAR(length=255),
                    type_=sa.String(length=16),
                    existing_nullable=False)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(u'phrase_default', 'meeting_type',
                    existing_type=sa.String(length=16),
                    type_=sa.VARCHAR(length=255),
                    existing_nullable=False)
    op.alter_column(u'meeting', 'meeting_type',
                    existing_type=sa.String(length=16),
                    type_=sa.VARCHAR(length=3),
                    existing_nullable=False)
    op.drop_table('meeting_type')
    ### end Alembic commands ###
