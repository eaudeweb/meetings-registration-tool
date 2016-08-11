from flask import url_for
from pyquery import PyQuery

from .factories import RoleUserMeetingFactory, UserFactory
from .factories import RoleFactory, JobFactory, MeetingFactory


def test_meeting_manager(app):
    meeting = MeetingFactory()

    first_role = RoleFactory(permissions=('manage_meeting',))
    second_role = RoleFactory(permissions=('view_participant',))

    first_role_user = RoleUserMeetingFactory(role=first_role,
                                             meeting=meeting)
    second_role_user = RoleUserMeetingFactory(role=second_role,
                                              meeting=meeting)

    JobFactory(user=first_role_user.user,
               meeting=first_role_user.meeting)
    JobFactory(user=second_role_user.user,
               meeting=first_role_user.meeting)

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = first_role_user.user.id

        resp = client.get(url_for('meetings.processing_file_list',
                                  meeting_id=meeting.id))
        assert resp.status_code == 200
        html = PyQuery(resp.data)
        assert html('#job-list tbody tr').length == 2


def test_superuser(app):
    role = RoleFactory(permissions=('view_participant',))
    role_user = RoleUserMeetingFactory(role=role)
    superuser = UserFactory(is_superuser=True)

    JobFactory(user=role_user.user,
               meeting=role_user.meeting)
    JobFactory(user=superuser,
               meeting=role_user.meeting)

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = superuser.id

        resp = client.get(url_for('meetings.processing_file_list',
                                  meeting_id=role_user.meeting.id))
        assert resp.status_code == 200
        html = PyQuery(resp.data)
        assert html('#job-list tbody tr').length == 2


def test_view_participant_user(app):
    meeting = MeetingFactory()

    first_role = RoleFactory(permissions=('view_participant',))
    second_role = RoleFactory(permissions=('view_participant',))

    first_role_user = RoleUserMeetingFactory(role=first_role,
                                             meeting=meeting)
    second_role_user = RoleUserMeetingFactory(role=second_role,
                                              meeting=meeting)

    JobFactory(user=first_role_user.user,
               meeting=first_role_user.meeting)
    JobFactory(user=second_role_user.user,
               meeting=first_role_user.meeting)

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = first_role_user.user.id

        resp = client.get(url_for('meetings.processing_file_list',
                                  meeting_id=meeting.id))
        assert resp.status_code == 200
        html = PyQuery(resp.data)
        assert html('#job-list tbody tr').length == 1


def test_user_without_permissions(app):
    user = UserFactory()
    meeting = MeetingFactory()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.get(url_for('meetings.processing_file_list',
                                  meeting_id=meeting.id))
        assert resp.status_code == 403
