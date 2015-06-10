import pytest
from flask import url_for
from testsuite.factories import RoleUserMeetingFactory, ParticipantFactory
from testsuite.factories import MeetingCategoryFactory, MediaParticipantFactory
from testsuite.factories import CustomFieldFactory, UserNotificationFactory
from testsuite.factories import PhraseMeetingFactory, StaffFactory
from testsuite.utils import add_participant_custom_fields

from mrt.models import Category


STATUS_OK = 200
STATUS_DENIED = 403


def _test(client, url, code):
    resp = client.get(url, follow_redirects=True)
    assert resp.status_code == code


def _login_user(client, user, password='eaudeweb'):
    return client.post(url_for('auth.login'), data=dict(
        email=user.email, password=password,
    ), follow_redirects=True)


@pytest.mark.parametrize("url_name, perms, status", [
    ('meetings.participants', [], STATUS_DENIED),
    ('meetings.participants', ('view_participant',), STATUS_OK),
    ('meetings.participants', ('manage_participant',), STATUS_OK),

    ('meetings.participant_detail', [], STATUS_DENIED),
    ('meetings.participant_detail', ('view_participant',), STATUS_OK),
    ('meetings.participant_detail', ('manage_participant',), STATUS_OK),

    ('meetings.participant_edit', [], STATUS_DENIED),
    ('meetings.participant_edit', ('view_participant',), STATUS_DENIED),
    ('meetings.participant_edit', ('manage_participant',), STATUS_OK),

    ('meetings.participant_badge', [], STATUS_DENIED),
    ('meetings.participant_badge', ('view_participant',), STATUS_OK),
    ('meetings.participant_badge', ('manage_participant',), STATUS_OK),

    ('meetings.participant_label', [], STATUS_DENIED),
    ('meetings.participant_label', ('view_participant',), STATUS_OK),
    ('meetings.participant_label', ('manage_participant',), STATUS_OK),

    ('meetings.participant_envelope', [], STATUS_DENIED),
    ('meetings.participant_envelope', ('view_participant',), STATUS_OK),
    ('meetings.participant_envelope', ('manage_participant',), STATUS_OK),

    ('meetings.participant_acknowledge_pdf', [], STATUS_DENIED),
    ('meetings.participant_acknowledge_pdf', ('view_participant',), STATUS_OK),
    ('meetings.participant_acknowledge_pdf',
        ('manage_participant',), STATUS_OK),

    ('meetings.participants_export', [], STATUS_DENIED),
    ('meetings.participants_export', ('view_participant',), STATUS_OK),
    ('meetings.participants_export', ('manage_participant',), STATUS_OK),
])
def test_permissions_participant(app, monkeypatch, pdf_renderer,
                                 url_name, perms, status, default_meeting,
                                 brand_dir):
    monkeypatch.setattr('mrt.meetings.participant.PdfRenderer', pdf_renderer)
    role = RoleUserMeetingFactory(role__permissions=perms)
    participant = ParticipantFactory(category__meeting=role.meeting)
    client = app.test_client()
    with app.test_request_context():
        add_participant_custom_fields(role.meeting)
        _login_user(client, role.user)
        _test(client, url_for(url_name,
                              participant_id=participant.id,
                              meeting_id=role.meeting.id), status)


@pytest.mark.parametrize("url_name, perms, status", [
    ('meetings.media_participants', [], STATUS_DENIED),
    ('meetings.media_participants', ('view_media_participant',), STATUS_OK),
    ('meetings.media_participants', ('manage_media_participant',), STATUS_OK),

    ('meetings.media_participant_detail', [], STATUS_DENIED),
    ('meetings.media_participant_detail', ('view_media_participant',),
        STATUS_OK),
    ('meetings.media_participant_detail', ('manage_media_participant',),
        STATUS_OK),

    ('meetings.media_participant_edit', [], STATUS_DENIED),
    ('meetings.media_participant_edit',
        ('view_media_participant',), STATUS_DENIED),
    ('meetings.media_participant_edit',
        ('manage_media_participant',), STATUS_OK),
])
def test_permissions_media_participant(app, url_name, perms, status,
                                       default_meeting):
    role = RoleUserMeetingFactory(role__permissions=perms)
    media = MediaParticipantFactory(category__meeting=role.meeting,
                                    category__category_type=Category.MEDIA)
    client = app.test_client()
    with app.test_request_context():
        _login_user(client, role.user)
        _test(client, url_for(url_name,
                              participant_id=media.id,
                              meeting_id=role.meeting.id), status)


@pytest.mark.parametrize("url_name, perms, status", [
    ('meetings.bulkemail', [], STATUS_DENIED),
    ('meetings.bulkemail', ('view_participant',), STATUS_DENIED),
    ('meetings.bulkemail', ('manage_participant',), STATUS_OK),

    ('meetings.participant_acknowledge', [], STATUS_DENIED),
    ('meetings.participant_acknowledge', ('view_participant',), STATUS_DENIED),
    ('meetings.participant_acknowledge', ('manage_participant',), STATUS_OK),
])
def test_permissions_emails(app, url_name, perms, status,
                            default_meeting):
    role = RoleUserMeetingFactory(role__permissions=perms)
    participant = ParticipantFactory(category__meeting=role.meeting)
    client = app.test_client()
    with app.test_request_context():
        _login_user(client, role.user)
        _test(client, url_for(url_name,
                              participant_id=participant.id,
                              meeting_id=role.meeting.id), status)


@pytest.mark.parametrize("url_name, perms, status", [
    ('meetings.categories', [], STATUS_DENIED),
    ('meetings.categories', ('manage_meeting',), STATUS_OK),

    ('meetings.category_edit', [], STATUS_DENIED),
    ('meetings.category_edit', ('manage_meeting',), STATUS_OK),
])
def test_permissions_meeting_category(app, url_name, perms, status,
                                      default_meeting):
    role = RoleUserMeetingFactory(role__permissions=perms)
    category = MeetingCategoryFactory(meeting=role.meeting)
    client = app.test_client()
    with app.test_request_context():
        _login_user(client, role.user)
        _test(client, url_for(url_name,
                              category_id=category.id,
                              meeting_id=role.meeting.id), status)


@pytest.mark.parametrize("url_name, perms, status", [
    ('meetings.roles', [], STATUS_DENIED),
    ('meetings.roles', ('manage_meeting',), STATUS_OK),

    ('meetings.role_user_edit', [], STATUS_DENIED),
    ('meetings.role_user_edit', ('manage_meeting',), STATUS_OK),

    ('meetings.role_meeting_change_owner', [], STATUS_DENIED),
    ('meetings.role_meeting_change_owner', ('manage_meeting'), STATUS_DENIED),
])
def test_permissions_meeting_role(app, url_name, perms, status,
                                  default_meeting):
    role = RoleUserMeetingFactory(role__permissions=perms)
    client = app.test_client()
    with app.test_request_context():
        _login_user(client, role.user)
        _test(client, url_for(url_name,
                              role_user_id=role.id,
                              meeting_id=role.meeting.id), status)


@pytest.mark.parametrize("url_name, perms, status", [
    ('meetings.notifications', [], STATUS_DENIED),
    ('meetings.notifications', ('manage_meeting',), STATUS_OK),

    ('meetings.notification_edit', [], STATUS_DENIED),
    ('meetings.notification_edit', ('manage_meeting',), STATUS_OK),
])
def test_permissions_meeting_notification(app, url_name, perms, status,
                                          default_meeting):
    role = RoleUserMeetingFactory(role__permissions=perms)
    notification = UserNotificationFactory(user=role.user,
                                           meeting=role.meeting)
    client = app.test_client()
    with app.test_request_context():
        _login_user(client, role.user)
        _test(client, url_for(url_name,
                              notification_id=notification.id,
                              meeting_id=role.meeting.id), status)


@pytest.mark.parametrize("url_name, perms, status", [
    ('meetings.phrase_edit', [], STATUS_DENIED),
    ('meetings.phrase_edit', ('manage_meeting',), STATUS_OK),
])
def test_permissions_meeting_phrase(app, url_name, perms, status,
                                    default_meeting):
    role = RoleUserMeetingFactory(role__permissions=perms)
    PhraseMeetingFactory(meeting=role.meeting)
    client = app.test_client()
    with app.test_request_context():
        _login_user(client, role.user)
        _test(client, url_for(url_name,
                              meeting_type='scc',
                              meeting_id=role.meeting.id), status)


@pytest.mark.parametrize("url_name, perms, status", [
    ('meetings.custom_fields', [], STATUS_DENIED),
    ('meetings.custom_fields', ('manage_meeting',), STATUS_OK),

    ('meetings.custom_field_edit', [], STATUS_DENIED),
    ('meetings.custom_field_edit', ('manage_meeting',), STATUS_OK),
])
def test_permissions_meeting_custom_field(app, url_name, perms, status,
                                          default_meeting):
    role = RoleUserMeetingFactory(role__permissions=perms)
    field = CustomFieldFactory(meeting=role.meeting)
    client = app.test_client()
    with app.test_request_context():
        _login_user(client, role.user)
        _test(client, url_for(url_name,
                              custom_field_id=field.id,
                              meeting_id=role.meeting.id), status)


@pytest.mark.parametrize("url_name, status", [
    ('meetings.participants', STATUS_OK),
    ('meetings.participant_detail', STATUS_OK),
    ('meetings.participant_edit', STATUS_OK),
    ('meetings.participant_badge', STATUS_OK),
    ('meetings.participant_label', STATUS_OK),
    ('meetings.participant_envelope', STATUS_OK),
])
def test_permissions_meeting_owner(app, url_name, status, default_meeting,
                                   monkeypatch, pdf_renderer, brand_dir):
    monkeypatch.setattr('mrt.meetings.participant.PdfRenderer', pdf_renderer)
    staff = StaffFactory()
    participant = ParticipantFactory(category__meeting__owner=staff)
    client = app.test_client()
    with app.test_request_context():
        add_participant_custom_fields(participant.meeting)
        _login_user(client, staff.user)
        _test(client, url_for(url_name,
                              participant_id=participant.id,
                              meeting_id=participant.meeting.id), status)


# TODO: printouts
