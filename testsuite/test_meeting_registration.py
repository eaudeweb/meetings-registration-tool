from flask import url_for
from pyquery import PyQuery

from mrt.mail import mail
from mrt.models import Participant, ActivityLog
from .factories import MeetingCategoryFactory, ParticipantFactory
from .factories import StaffFactory, RoleUserMeetingFactory
from .factories import UserNotificationFactory

from testsuite.utils import add_participant_custom_fields
from testsuite.utils import populate_participant_form


def test_meeting_online_resistration_open(app):
    category = MeetingCategoryFactory(meeting__online_registration=True)

    client = app.test_client()
    with app.test_request_context():
        add_participant_custom_fields(category.meeting)
        resp = client.get(url_for('meetings.registration',
                                  meeting_id=category.meeting.id))
        assert PyQuery(resp.data)('form').length == 1


def test_meeting_online_registration_closed(app):
    category = MeetingCategoryFactory(meeting__online_registration=False)

    client = app.test_client()
    with app.test_request_context():
        add_participant_custom_fields(category.meeting)
        resp = client.get(url_for('meetings.registration',
                                  meeting_id=category.meeting.id))
        html = PyQuery(resp.data)
        assert html('form').length == 0
        assert html('.alert').length == 1


def test_meeting_online_registration_add(app):
    category = MeetingCategoryFactory(meeting__online_registration=True)
    meeting = category.meeting
    role_user = RoleUserMeetingFactory(meeting=meeting)
    RoleUserMeetingFactory(meeting=meeting,
                           user__email='test@email.com')
    StaffFactory(user=role_user.user)
    UserNotificationFactory(user=role_user.user, meeting=meeting)

    data = ParticipantFactory.attributes()
    data['category_id'] = category.id

    client = app.test_client()
    with app.test_request_context(), mail.record_messages() as outbox:
        add_participant_custom_fields(meeting)
        populate_participant_form(meeting, data)
        resp = client.post(url_for('meetings.registration',
                                   meeting_id=meeting.id), data=data)

        assert resp.status_code == 200
        assert Participant.query.filter_by(meeting=meeting).count() == 1
        assert len(outbox) == 2
        assert ActivityLog.query.filter_by(meeting=meeting).count() == 1
