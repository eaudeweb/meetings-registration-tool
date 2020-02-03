"""Rename sex to gender

Revision ID: 8bdd8fe4f960
Revises: 96153f452c5e
Create Date: 2020-02-03 07:37:30.153752

"""

# revision identifiers, used by Alembic.
revision = '8bdd8fe4f960'
down_revision = '96153f452c5e'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("ALTER TABLE participant RENAME sex TO gender;")
    op.execute("UPDATE custom_field SET slug='gender' WHERE slug='sex'")
    op.execute("UPDATE translation SET english='Gender' WHERE english='Sex'")


def downgrade():
    op.execute("ALTER TABLE participant RENAME gender TO sex;")
    op.execute("UPDATE custom_field SET slug='sex' where slug='gender'")
    op.execute("UPDATE translation SET english='Sex' WHERE english='Gender'")
