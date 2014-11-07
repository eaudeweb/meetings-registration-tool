"""Default meeting insertion

Revision ID: 558d8948b61f
Revises: 2a0c02c3cfc
Create Date: 2014-11-07 15:30:47.619809

"""

# revision identifiers, used by Alembic.
revision = '558d8948b61f'
down_revision = '2a0c02c3cfc'

from datetime import date
from sqlalchemy_utils.types.country import Country
from mrt.models import Meeting, Translation, db
from mrt.forms.meetings.meeting import add_custom_fields_for_meeting


def upgrade():
    default_meeting_title = Translation(english="Default Meeting")
    default_meeting = Meeting(title=default_meeting_title,
                              badge_header=default_meeting_title,
                              acronym="DEFAULT",
                              meeting_type=Meeting.DEFAULT_TYPE,
                              date_start=date.today(),
                              date_end=date.today(),
                              venue_city=default_meeting_title,
                              venue_country=Country("RO"),
                              online_registration=False)
    db.session.add(default_meeting)
    add_custom_fields_for_meeting(default_meeting)
    db.session.commit()


def downgrade():
    meeting = Meeting.query.filter_by(meeting_type=Meeting.DEFAULT_TYPE).one()
    db.session.delete(meeting)
    db.session.commit()
