"""Insert default meeting.

Revision ID: 1d70ecd3db0d
Revises: 29ecac35d8b2
Create Date: 2014-12-16 18:24:44.906930

"""

# revision identifiers, used by Alembic.
revision = '1d70ecd3db0d'
down_revision = '29ecac35d8b2'

from alembic import op
from datetime import date
from mrt.models import Meeting, MeetingType, Translation


translation_table = Translation.__table__
meeting_type_table = MeetingType.__table__
meeting_table = Meeting.__table__


def upgrade():
    conn = op.get_bind()
    res = conn.execute(
        translation_table.insert().values({'english': 'Default Meeting'})
    )
    [title_id] = res.inserted_primary_key
    res = conn.execute(
        meeting_type_table.insert().values(
            {'slug': 'def',  'label': 'Default Meeting', 'default': True})
    )
    [meeting_type] = res.inserted_primary_key
    conn.execute(
        meeting_table.insert().values({
            'title_id': title_id,
            'badge_header_id': title_id,
            'acronym': op.inline_literal('DEFAULT'),
            'date_start': op.inline_literal(date.today().isoformat()),
            'date_end': op.inline_literal(date.today().isoformat()),
            'venue_city_id': op.inline_literal(title_id),
            'venue_country': op.inline_literal('RO'),
            'meeting_type': op.inline_literal(meeting_type),
        })
    )


def downgrade():
    conn = op.get_bind()
    sel = (
        meeting_type_table.select()
        .where(meeting_type_table.c.default == op.inline_literal(True))
        .with_only_columns(['slug'])
    )
    [default_meeting_type] = conn.execute(sel).fetchone()
    sel = (
        meeting_table.select()
        .where(meeting_table.c.meeting_type ==
               op.inline_literal(default_meeting_type))
        .with_only_columns(['title_id'])
    )
    [title_id] = conn.execute(sel).fetchone()
    conn.execute(
        meeting_table.delete()
        .where(meeting_table.c.meeting_type ==
               op.inline_literal(default_meeting_type))
    )
    conn.execute(
        translation_table.delete()
        .where(translation_table.c.id == op.inline_literal(title_id))
    )
    conn.execute(
        meeting_type_table.delete()
        .where(meeting_type_table.c.slug ==
               op.inline_literal(default_meeting_type))
    )
