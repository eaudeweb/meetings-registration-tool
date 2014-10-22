from flask import url_for
from pyquery import PyQuery

from .factories import MeetingCategoryFactory

from testsuite.utils import add_participant_custom_fields


def test_meeting_online_resistration_open(app):
    category = MeetingCategoryFactory(meeting__online_registration=True)

    client = app.test_client()
    with app.test_request_context():
        add_participant_custom_fields(category.meeting)
        resp = client.get(url_for('meetings.registration',
                                  meeting_id=category.meeting.id))
        assert PyQuery(resp.data)('form').length


def test_meeting_online_registration_closed(app):
    category = MeetingCategoryFactory(meeting__online_registration=False)

    client = app.test_client()
    with app.test_request_context():
        add_participant_custom_fields(category.meeting)
        resp = client.get(url_for('meetings.registration',
                                  meeting_id=category.meeting.id))
        html = PyQuery(resp.data)
        assert html('form').length == 0
        assert html('.alert').length
