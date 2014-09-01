from flask import url_for

from mrt.mail import mail
from mrt.models import MailLog
from .factories import MeetingCategoryFactory, ParticipantFactory
from .factories import MailLogFactory, RoleUserFactory


PERMISSION = ('view_participant', )


def test_send_email_in_english(app):
    cat = MeetingCategoryFactory()
    role_user = RoleUserFactory(role__permissions=PERMISSION)
    ParticipantFactory.create_batch(5, meeting=cat.meeting)
    ParticipantFactory.create_batch(5, meeting=cat.meeting, language='fr')
    data = {
        'message': 'Test',
        'subject': 'Test subject',
        'language': 'en'
    }

    client = app.test_client()
    with app.test_request_context(), mail.record_messages() as outbox:
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        resp = client.post(url_for('meetings.bulkemail',
                                   meeting_id=cat.meeting.id), data=data)
        assert resp.status_code == 302
        assert len(outbox) == 5


def test_send_email_to_categories(app):
    role_user = RoleUserFactory(role__permissions=PERMISSION)
    cat_member = MeetingCategoryFactory()
    cat_press = MeetingCategoryFactory(meeting=cat_member.meeting)
    ParticipantFactory.create_batch(7, meeting=cat_member.meeting,
                                    category=cat_member)
    ParticipantFactory.create_batch(4, meeting=cat_member.meeting,
                                    category=cat_press)
    data = {
        'message': 'Test',
        'subject': 'Test subject',
        'language': 'en',
        'categories': '1'
    }

    client = app.test_client()
    with app.test_request_context(), mail.record_messages() as outbox:
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        resp = client.post(url_for('meetings.bulkemail',
                                   meeting_id=cat_press.meeting.id), data=data)
        assert resp.status_code == 302
        assert len(outbox) == 7


def test_resend_email(app):
    role_user = RoleUserFactory(role__permissions=PERMISSION)
    mail_log = MailLogFactory()

    client = app.test_client()
    with app.test_request_context(), mail.record_messages() as outbox:
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        resp = client.post(url_for('meetings.mail_resend',
                                   meeting_id=mail_log.meeting.id,
                                   mail_id=mail_log.id))
        assert resp.status_code == 302
        assert len(outbox) == 1
        assert MailLog.query.count() == 2
