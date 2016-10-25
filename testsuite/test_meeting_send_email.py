from flask import url_for
from pyquery import PyQuery

from mrt.mail import mail
from mrt.models import MailLog, Participant
from .factories import MeetingCategoryFactory, ParticipantFactory
from .factories import MailLogFactory


def test_send_email_in_english(app, user):
    cat = MeetingCategoryFactory()
    ParticipantFactory.create_batch(5, meeting=cat.meeting)
    ParticipantFactory.create_batch(5, meeting=cat.meeting, language='French')
    data = {
        'message': 'Test',
        'subject': 'Test subject',
        'language': 'English',
        'participant_type': 'participant',
    }

    client = app.test_client()
    with app.test_request_context(), mail.record_messages() as outbox:
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('meetings.bulkemail',
                                   meeting_id=cat.meeting.id), data=data)
        assert resp.status_code == 302
        assert len(outbox) == 5


def test_send_email_to_all_participants(app, user):
    cat = MeetingCategoryFactory()
    ParticipantFactory.create_batch(5, meeting=cat.meeting)
    ParticipantFactory.create_batch(5, meeting=cat.meeting, language='French')
    data = {
        'message': 'Test',
        'subject': 'Test subject',
        'language': 'all',
        'participant_type': 'participant',
    }

    client = app.test_client()
    with app.test_request_context(), mail.record_messages() as outbox:
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('meetings.bulkemail',
                                   meeting_id=cat.meeting.id), data=data)
        assert resp.status_code == 302
        assert len(outbox) == 10


def test_send_email_to_categories(app, user):
    cat_member = MeetingCategoryFactory()
    cat_press = MeetingCategoryFactory(meeting=cat_member.meeting)
    ParticipantFactory.create_batch(7, meeting=cat_member.meeting,
                                    category=cat_member)
    ParticipantFactory.create_batch(4, meeting=cat_member.meeting,
                                    category=cat_press)
    data = {
        'message': 'Test',
        'subject': 'Test subject',
        'language': 'English',
        'categories': '1',
        'participant_type': 'participant',
    }

    client = app.test_client()
    with app.test_request_context(), mail.record_messages() as outbox:
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('meetings.bulkemail',
                                   meeting_id=cat_press.meeting.id), data=data)
        assert resp.status_code == 302
        assert len(outbox) == 7


def test_meeting_bulk_email_recipients(app, user):
    cat = MeetingCategoryFactory()
    cat_press = MeetingCategoryFactory(meeting=cat.meeting,
                                       category_type=Participant.MEDIA)
    ParticipantFactory.create_batch(5, meeting=cat.meeting)
    ParticipantFactory.create_batch(5, meeting=cat.meeting,
                                    language='Spanish')
    ParticipantFactory.create_batch(4, meeting=cat.meeting,
                                    category=cat_press,
                                    participant_type=Participant.MEDIA)

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.get(url_for('meetings.recipients',
                                  meeting_id=cat.meeting.id,
                                  language='English'))
        assert resp.status_code == 200
        assert len(PyQuery(resp.data)('#recipients tbody tr')) == 9
        resp = client.get(url_for('meetings.recipients',
                                  meeting_id=cat.meeting.id,
                                  language='Spanish'))
        assert resp.status_code == 200
        assert len(PyQuery(resp.data)('#recipients tbody tr')) == 5
        resp = client.get(url_for('meetings.recipients',
                                  meeting_id=cat.meeting.id,
                                  language='English',
                                  participant_type=Participant.MEDIA))
        assert resp.status_code == 200
        assert len(PyQuery(resp.data)('#recipients tbody tr')) == 4
        resp = client.get(url_for('meetings.recipients',
                                  meeting_id=cat.meeting.id,
                                  language='English',
                                  participant_type=Participant.MEDIA))
        assert resp.status_code == 200
        assert len(PyQuery(resp.data)('#recipients tbody tr')) == 4


def test_send_bulk_email_logs(app, user):
    cat = MeetingCategoryFactory()
    ParticipantFactory.create_batch(5, meeting=cat.meeting)
    ParticipantFactory.create_batch(3, meeting=cat.meeting,
                                    language='French')

    data = {
        'message': 'Test',
        'subject': 'Test subject',
        'language': 'English',
        'participant_type': 'participant',
    }

    client = app.test_client()
    with app.test_request_context(), mail.record_messages() as outbox:
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('meetings.bulkemail',
                                   meeting_id=cat.meeting.id), data=data)
        assert resp.status_code == 302
        assert len(outbox) == 5
        assert MailLog.query.filter_by(meeting=cat.meeting).count() == 5

        resp = client.get(url_for('meetings.mail_logs',
                                  meeting_id=cat.meeting.id))
        assert resp.status_code == 200
        assert len(PyQuery(resp.data)('#mails tbody tr')) == 5


def test_resend_email(app, user):
    mail_log = MailLogFactory()

    client = app.test_client()
    with app.test_request_context(), mail.record_messages() as outbox:
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('meetings.mail_resend',
                                   meeting_id=mail_log.meeting.id,
                                   mail_id=mail_log.id))
        assert resp.status_code == 302
        assert len(outbox) == 1
        assert MailLog.query.count() == 2


def test_ack_email(app, user):
    cat = MeetingCategoryFactory()
    participant = ParticipantFactory(meeting=cat.meeting)
    client = app.test_client()
    data = {
        'message': 'Test',
        'subject': 'Very long subject '*8,
        'language': 'English',
        'to': participant.email,
    }
    with app.test_request_context(), mail.record_messages() as outbox:
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('meetings.participant_acknowledge',
                                   meeting_id=cat.meeting.id,
                                   participant_id=participant.id),
                           data=data)
        assert resp.status_code == 200
        assert len(PyQuery(resp.data)('div.text-danger')) == 1
        assert PyQuery(resp.data)('div.text-danger')[0].text_content() == \
            'Field cannot be longer than 128 characters.'
        assert len(outbox) == 0
        assert MailLog.query.count() == 0
