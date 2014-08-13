from flask import url_for, g
from testsuite.factories import RoleUserMeetingFactory, ParticipantFactory, \
    MediaParticipantFactory


STATUS_OK = 200
STATUS_DENIED = 403


def _test(client, url, code):
    resp = client.get(url)
    assert resp.status_code == code


def _login_user(client, user, password='eaudeweb'):
    return client.post(url_for('auth.login'), data=dict(
        email=user.email, password=password,
    ), follow_redirects=True)


def test_staff_no_access(app):
    role = RoleUserMeetingFactory(role__permissions=[])
    client = app.test_client()
    with app.test_request_context():
        _login_user(client, role.user)
        _test(client, url_for('meetings.participants',
                              meeting_id=role.meeting.id), STATUS_DENIED)

        _test(client, url_for('meetings.media_participants',
                              meeting_id=role.meeting.id), STATUS_DENIED)


def test_viewer_read_access_participants(app):
    perms = ('view_participant',)
    role = RoleUserMeetingFactory(role__permissions=perms)
    participant = ParticipantFactory(category__meeting=role.meeting)
    client = app.test_client()
    with app.test_request_context():
        _login_user(client, role.user)
        _test(client, url_for('meetings.participants',
                              meeting_id=role.meeting.id), STATUS_OK)
        _test(client, url_for('meetings.participant_edit',
                              meeting_id=role.meeting.id,
                              participant_id=participant.id), STATUS_DENIED)


def test_viewer_read_access_media_participants(app):
    perms = ('view_media_participant',)
    role = RoleUserMeetingFactory(role__permissions=perms)
    participant = MediaParticipantFactory(category__meeting=role.meeting)
    client = app.test_client()
    with app.test_request_context():
        _login_user(client, role.user)
        _test(client, url_for('meetings.media_participants',
                              meeting_id=role.meeting.id), STATUS_OK)
        _test(client, url_for('meetings.media_participant_edit',
                              meeting_id=role.meeting.id,
                              participant_id=participant.id), STATUS_DENIED)


def test_manager_full_access_participants(app):
    perms = ('manage_participant', 'view_participant')
    role = RoleUserMeetingFactory(role__permissions=perms)
    participant = ParticipantFactory(category__meeting=role.meeting)
    client = app.test_client()
    with app.test_request_context():
        _login_user(client, role.user)
        _test(client, url_for('meetings.participants',
                              meeting_id=role.meeting.id), STATUS_OK)
        _test(client, url_for('meetings.participant_edit',
                              meeting_id=role.meeting.id,
                              participant_id=participant.id), STATUS_OK)


def test_manager_full_access_media_participants(app):
    perms = ('manage_media_participant', 'view_media_participant')
    role = RoleUserMeetingFactory(role__permissions=perms)
    participant = MediaParticipantFactory(category__meeting=role.meeting)
    client = app.test_client()
    with app.test_request_context():
        _login_user(client, role.user)
        _test(client, url_for('meetings.media_participants',
                              meeting_id=role.meeting.id), STATUS_OK)
        _test(client, url_for('meetings.media_participant_edit',
                              meeting_id=role.meeting.id,
                              participant_id=participant.id), STATUS_OK)


# TODO: printouts, emails, settings.
