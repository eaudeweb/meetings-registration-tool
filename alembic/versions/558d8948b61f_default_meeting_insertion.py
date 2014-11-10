"""Default meeting insertion

Revision ID: 558d8948b61f
Revises: 2a0c02c3cfc
Create Date: 2014-11-07 15:30:47.619809

"""

# revision identifiers, used by Alembic.
revision = '558d8948b61f'
down_revision = '2a0c02c3cfc'

from alembic import op
from datetime import date
from mrt.models import Meeting, Translation


translation_table = Translation.__table__
meeting_table = Meeting.__table__


def upgrade():
    conn = op.get_bind()
    res = conn.execute(
        translation_table.insert().values({'english': 'Default Meeting'})
    )
    [title_id] = res.inserted_primary_key
    conn.execute(
        meeting_table.insert().values({
            'title_id': title_id,
            'badge_header_id': title_id,
            'acronym': op.inline_literal('DEFAULT'),
            'date_start': op.inline_literal(date.today().isoformat()),
            'date_end': op.inline_literal(date.today().isoformat()),
            'venue_city_id': op.inline_literal(title_id),
            'venue_country': op.inline_literal('RO'),
            'meeting_type': op.inline_literal(Meeting.DEFAULT_TYPE),
        })
    )


def downgrade():
    conn = op.get_bind()
    sel = (
        meeting_table.select()
        .where(meeting_table.c.meeting_type ==
               op.inline_literal(Meeting.DEFAULT_TYPE))
        .with_only_columns(['title_id'])
    )
    [title_id] = conn.execute(sel).fetchone()
    conn.execute(
        meeting_table.delete()
        .where(meeting_table.c.meeting_type ==
               op.inline_literal(Meeting.DEFAULT_TYPE))
    )
    conn.execute(
        translation_table.delete()
        .where(translation_table.c.id == op.inline_literal(title_id))
    )
