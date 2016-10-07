import pytest
from flask import url_for
from pyquery import PyQuery
from testsuite.factories import RoleUserMeetingFactory, ParticipantFactory
from testsuite.factories import MediaParticipantFactory, StaffFactory
from testsuite.factories import MeetingFactory
from testsuite.utils import add_participant_custom_fields
from mrt.forms.meetings.meeting import MediaParticipantDummyForm

from mrt.models import Category


MEDIA_ENABLED = {'media_participant_enabled': True}
DISPLAYED = 1
HIDDEN = 0


def _test(client, url, element_id, status):
    resp = client.get(url, follow_redirects=True)
    assert resp.status_code == 200
    element = PyQuery(resp.data)(element_id)
    assert len(element) == status
    # PYQUERY CHECKS HERE!!


def _login_user(client, user, password='eaudeweb'):
    return client.post(url_for('auth.login'), data=dict(
        email=user.email, password=password
    ), follow_redirects=True)


@pytest.mark.parametrize("url_name, perms, element_id, status", [
    ('meetings.participants', ('view_participant',),
        '#participants_tab', DISPLAYED),
    ('meetings.participants', ('manage_participant',),
        '#participants_tab', DISPLAYED),
    ('meetings.participants', ('manage_meeting',),
        '#participants_tab', DISPLAYED),
    ('meetings.participants', ('manage_participant',),
        '#media_participants_tab', HIDDEN),
    ('meetings.participants', ('manage_meeting',),
        '#media_participants_tab', DISPLAYED),
    ('meetings.media_participants', ('view_media_participant',),
        '#media_participants_tab', DISPLAYED),
    ('meetings.media_participants', ('manage_media_participant',),
        '#media_participants_tab', DISPLAYED),
    ('meetings.media_participants', ('manage_media_participant',),
        '#participants_tab', HIDDEN),
    ('meetings.participants', ('manage_meeting',),
        '#printouts_tab', DISPLAYED),
    ('meetings.participants', ('manage_participant',),
        '#printouts_tab', DISPLAYED),
    ('meetings.participants', ('view_participant',),
        '#printouts_tab', DISPLAYED),
    ('meetings.media_participants', ('view_media_participant',),
        '#printouts_tab', DISPLAYED),  # Excel download works as a printout now
    ('meetings.participants', ('manage_meeting',),
        '#email_tab', DISPLAYED),
    ('meetings.participants', ('manage_participant',),
        '#email_tab', DISPLAYED),
    ('meetings.participants', ('view_participant',),
        '#email_tab', HIDDEN),
    ('meetings.participants', ('manage_meeting',),
        '#settings_tab', DISPLAYED),
    ('meetings.participants', ('view_participant',),
        '#settings_tab', HIDDEN),
    ('meetings.participants', ('manage_meeting',),
        '#participant_add', DISPLAYED),
    ('meetings.participants', ('manage_participant',),
        '#participant_add', DISPLAYED),
    ('meetings.participants', ('view_participant',),
        '#participant_add', HIDDEN),
    ('meetings.media_participants', ('manage_meeting',),
        '#media_participant_add', DISPLAYED),
    ('meetings.media_participants', ('manage_media_participant',),
        '#media_participant_add', DISPLAYED),
    ('meetings.media_participants', ('view_media_participant',),
        '#media_participant_add', HIDDEN),
    ('meetings.roles', ('manage_meeting',), '.glyphicon-user', HIDDEN)
])
def test_meeting_tab_menu(app, url_name, perms, element_id, status):
    role = RoleUserMeetingFactory(role__permissions=perms,
                                  meeting__settings=MEDIA_ENABLED)
    client = app.test_client()
    with app.test_request_context():
        add_participant_custom_fields(role.meeting)
        add_participant_custom_fields(role.meeting, MediaParticipantDummyForm)
        _login_user(client, role.user)
        _test(client, url_for(url_name, meeting_id=role.meeting_id),
              element_id, status)


@pytest.mark.parametrize("url_name, perms, element_id, status", [
    ('meetings.participant_detail', ('view_participant',),
        '#ack_email', HIDDEN),
    ('meetings.participant_detail', ('manage_participant',),
        '#ack_email', DISPLAYED),
    ('meetings.participant_detail', ('manage_meeting',),
        '#ack_email', DISPLAYED),
    ('meetings.participant_detail', ('view_participant',),
        '#participant_delete', HIDDEN),
    ('meetings.participant_detail', ('manage_participant',),
        '#participant_delete', DISPLAYED),
    ('meetings.participant_detail', ('manage_meeting',),
        '#participant_delete', DISPLAYED),
    ('meetings.participant_detail', ('view_participant',),
        '#participant_edit', HIDDEN),
    ('meetings.participant_detail', ('manage_participant',),
        '#participant_edit', DISPLAYED),
    ('meetings.participant_detail', ('manage_meeting',),
        '#participant_edit', DISPLAYED),
])
def test_meeting_participant_buttons(app, url_name, perms,
                                     element_id, status):
    role = RoleUserMeetingFactory(role__permissions=perms,
                                  meeting__settings=MEDIA_ENABLED)
    participant = ParticipantFactory(category__meeting=role.meeting)
    client = app.test_client()
    with app.test_request_context():
        _login_user(client, role.user)
        _test(client, url_for(url_name, meeting_id=role.meeting_id,
                              participant_id=participant.id),
              element_id, status)


@pytest.mark.parametrize("url_name, perms, element_id, status", [
    ('meetings.media_participant_detail', ('view_media_participant',),
        '#media_participant_delete', HIDDEN),
    ('meetings.media_participant_detail', ('manage_media_participant',),
        '#media_participant_delete', DISPLAYED),
    ('meetings.media_participant_detail', ('manage_meeting',),
        '#media_participant_delete', DISPLAYED),
    ('meetings.media_participant_detail', ('view_media_participant',),
        '#media_participant_edit', HIDDEN),
    ('meetings.media_participant_detail', ('manage_media_participant',),
        '#media_participant_edit', DISPLAYED),
    ('meetings.media_participant_detail', ('manage_meeting',),
        '#media_participant_edit', DISPLAYED),
])
def test_meeting_media_participant_buttons(app, url_name, perms,
                                           element_id, status):
    role = RoleUserMeetingFactory(role__permissions=perms,
                                  meeting__settings=MEDIA_ENABLED)
    media = MediaParticipantFactory(category__meeting=role.meeting,
                                    category__category_type=Category.MEDIA)
    client = app.test_client()
    with app.test_request_context():
        _login_user(client, role.user)
        _test(client, url_for(url_name, meeting_id=role.meeting_id,
                              participant_id=media.id),
              element_id, status)


@pytest.mark.parametrize("url_name, element_id, status", [
    ('meetings.participants', '#participants_tab', DISPLAYED),
    ('meetings.participants', '#media_participants_tab', DISPLAYED),
    ('meetings.participants', '#printouts_tab', DISPLAYED),
    ('meetings.participants', '#printouts_tab', DISPLAYED),
    ('meetings.participants', '#email_tab', DISPLAYED),
    ('meetings.roles', '.glyphicon-user', HIDDEN)
])
def test_meeting_owner_tab_menu(app, url_name, element_id, status):
    owner = StaffFactory()
    meeting = MeetingFactory(settings=MEDIA_ENABLED,
                             owner=owner)

    client = app.test_client()
    with app.test_request_context():
        add_participant_custom_fields(meeting)
        _login_user(client, owner.user)
        _test(client, url_for(url_name, meeting_id=meeting.id),
              element_id, status)


@pytest.mark.parametrize("url_name, element_id, status", [
    ('meetings.participant_detail', '#ack_email', DISPLAYED),
    ('meetings.participant_detail', '#participant_delete', DISPLAYED),
    ('meetings.participant_detail', '#participant_edit', DISPLAYED),
])
def test_meeting_owner_participant_buttons(app, url_name, element_id, status):
    owner = StaffFactory()
    meeting = MeetingFactory(settings=MEDIA_ENABLED,
                             owner=owner)
    participant = ParticipantFactory(category__meeting=meeting)
    client = app.test_client()
    with app.test_request_context():
        _login_user(client, owner.user)
        _test(client, url_for(url_name, meeting_id=meeting.id,
                              participant_id=participant.id),
              element_id, status)


@pytest.mark.parametrize("url_name, element_id, status", [
    ('meetings.media_participant_detail',
        '#media_participant_delete', DISPLAYED),
    ('meetings.media_participant_detail',
        '#media_participant_edit', DISPLAYED),
])
def test_meeting_owner_media_participant_buttons(app, url_name, element_id,
                                                 status):
    owner = StaffFactory()
    meeting = MeetingFactory(settings=MEDIA_ENABLED,
                             owner=owner)
    media = MediaParticipantFactory(category__meeting=meeting,
                                    category__category_type=Category.MEDIA)
    client = app.test_client()
    with app.test_request_context():
        _login_user(client, owner.user)
        _test(client, url_for(url_name, meeting_id=meeting.id,
                              participant_id=media.id),
              element_id, status)


@pytest.mark.parametrize("url_name, element_id, status", [
    ('meetings.participants', '#participants_tab', DISPLAYED),
    ('meetings.participants', '#media_participants_tab', DISPLAYED),
    ('meetings.participants', '#printouts_tab', DISPLAYED),
    ('meetings.participants', '#printouts_tab', DISPLAYED),
    ('meetings.participants', '#email_tab', DISPLAYED),
    ('meetings.roles', '.glyphicon-user', DISPLAYED),
    ('meetings.roles', '#admin_dropdown', DISPLAYED)
])
def test_meeting_superuser_sees_everything(app, user, url_name, element_id,
                                           status):
    meeting = MeetingFactory(settings=MEDIA_ENABLED)
    client = app.test_client()
    with app.test_request_context():
        add_participant_custom_fields(meeting)
        _login_user(client, user)
        _test(client, url_for(url_name, meeting_id=meeting.id),
              element_id, status)
