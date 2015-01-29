from flask import url_for
from pyquery import PyQuery

from mrt.definitions import NOTIFICATION_TYPES, NOTIFY_PARTICIPANT
from mrt.models import RoleUser, Category, UserNotification
from mrt.mail import mail
from mrt.forms.meetings import (add_custom_fields_for_meeting,
                                MediaParticipantDummyForm)
from .factories import MeetingCategoryFactory, ParticipantFactory
from .factories import UserNotificationFactory, RoleUserMeetingFactory
from .factories import MediaParticipantFactory, MeetingFactory

from .utils import add_participant_custom_fields, populate_participant_form


def test_send_notification_add_participant(app):
    category = MeetingCategoryFactory()
    role_user = RoleUserMeetingFactory(meeting=category.meeting)
    RoleUserMeetingFactory(meeting=category.meeting,
                           user__email='test@email.com')
    UserNotificationFactory(user=role_user.user, meeting=category.meeting)

    data = ParticipantFactory.attributes()
    data['category_id'] = category.id

    client = app.test_client()
    with app.test_request_context(), mail.record_messages() as outbox:
        add_participant_custom_fields(category.meeting)
        populate_participant_form(category.meeting, data)
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        resp = client.post(url_for('meetings.participant_edit',
                                   meeting_id=category.meeting.id), data=data)
        assert resp.status_code == 302
        assert RoleUser.query.filter_by(meeting=category.meeting).count() == 2
        assert len(outbox) == 0


def test_send_notification_add_media_participant(app):
    category = (
        MeetingCategoryFactory(meeting__settings='media_participant_enabled',
                               category_type=Category.MEDIA))
    role_user = RoleUserMeetingFactory(meeting=category.meeting)
    RoleUserMeetingFactory(meeting=category.meeting,
                           user__email='test@email.com')
    UserNotificationFactory(user=role_user.user, meeting=category.meeting,
                            notification_type='notify_media_participant')

    data = MediaParticipantFactory.attributes()
    data['category_id'] = category.id

    client = app.test_client()
    with app.test_request_context(), mail.record_messages() as outbox:
        add_custom_fields_for_meeting(category.meeting,
                                      form_class=MediaParticipantDummyForm)
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        resp = client.post(url_for('meetings.media_participant_edit',
                                   meeting_id=category.meeting.id), data=data)
        assert resp.status_code == 302
        assert RoleUser.query.filter_by(meeting=category.meeting).count() == 2
        assert len(outbox) == 0


def test_notification_types_with_media_enabled(app, user):
    MEDIA_ENABLED = {'media_participant_enabled': True}
    meeting = MeetingFactory(settings=MEDIA_ENABLED)

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.get(url_for('meetings.notification_edit',
                                  meeting_id=meeting.id))
        type_options = PyQuery(resp.data)('#notification_type option')
        assert len(type_options) == 2
        for i, option in enumerate(type_options):
            option_value = (option.attrib['value'], option.text)
            assert option_value == NOTIFICATION_TYPES[i]


def test_notification_types_with_media_disabled(app, user):
    meeting = MeetingFactory()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.get(url_for('meetings.notification_edit',
                                  meeting_id=meeting.id))
        type_options = PyQuery(resp.data)('#notification_type option')
        assert len(type_options) == 1
        option_value = (type_options[0].attrib['value'], type_options[0].text)
        assert option_value == NOTIFY_PARTICIPANT


def test_notify_media_with_media_disabled(app, user):
    meeting = MeetingFactory()
    role_user = RoleUserMeetingFactory(meeting=meeting)

    data = {
        'notification_type': 'notify_media_participant',
        'user_id': role_user.user.id
    }

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('meetings.notification_edit',
                                   meeting_id=meeting.id), data=data)
        assert resp.status_code == 200
        assert UserNotification.query.count() == 0
        errors = PyQuery(resp.data)('.text-danger small')
        assert len(errors) == 1
        assert errors.text() == 'Not a valid choice'
