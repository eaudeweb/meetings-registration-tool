
from flask import current_app as app
from flask import g


"""
Helpers for meeting urls
"""


def add_meeting_id(endpoint, values):
    meeting = getattr(g, 'meeting', None)
    if 'meeting_id' in values or not meeting:
        return
    if app.url_map.is_endpoint_expecting(endpoint, 'meeting_id'):
        values.setdefault('meeting_id', meeting.id)
    if app.url_map.is_endpoint_expecting(endpoint, 'meeting_acronym'):
        values.setdefault('meeting_acronym', meeting.acronym)


def add_meeting_global(endpoint, values):
    from mrt.models import Meeting

    g.meeting = None
    if app.url_map.is_endpoint_expecting(endpoint, 'meeting_id'):
        meeting_id = values.pop('meeting_id', None)
        if meeting_id:
            g.meeting = Meeting.query.get_or_404(meeting_id)
    if app.url_map.is_endpoint_expecting(endpoint, 'meeting_acronym'):
        acronym = values.pop('meeting_acronym', None)
        if acronym:
            g.meeting = Meeting.query.filter_by(acronym=acronym).first_or_404()
