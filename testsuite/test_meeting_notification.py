from flask import url_for

from mrt.models import RoleUser, Category
from mrt.mail import mail
from mrt.forms.meetings import (add_custom_fields_for_meeting,
                                MediaParticipantDummyForm)
from .factories import MeetingCategoryFactory, ParticipantFactory
from .factories import UserNotificationFactory, RoleUserMeetingFactory
from .factories import MediaParticipantFactory

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
        assert len(outbox) == 1


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
        assert len(outbox) == 1
