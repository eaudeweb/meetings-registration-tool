from flask import url_for
from pyquery import PyQuery

from mrt.models import db

from .factories import RoleUserMeetingFactory
from .factories import RoleFactory, JobFactory, MeetingFactory


def test_meeting_manager(app):
    meeting = MeetingFactory()

    first_role = RoleFactory(permissions=('manage_meeting',))
    second_role = RoleFactory(permissions=('view_participant',))

    first_role_user = RoleUserMeetingFactory(role=first_role,
                                             meeting=meeting)
    second_role_user = RoleUserMeetingFactory(role=second_role,
                                              meeting=meeting)

    first_job = JobFactory(user_id=first_role_user.user.id,
                           meeting_id=first_role_user.meeting.id)
    second_job = JobFactory(user_id=second_role_user.user.id,
                            meeting_id=first_role_user.meeting.id)

    db.session.add(first_job)
    db.session.add(second_job)
    db.session.commit()

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
    meeting = MeetingFactory()

    first_role = RoleFactory(permissions=('',))
    second_role = RoleFactory(permissions=('view_participant',))

    first_role_user = RoleUserMeetingFactory(role=first_role,
                                             meeting=meeting)
    second_role_user = RoleUserMeetingFactory(role=second_role,
                                              meeting=meeting)

    first_role_user.user.is_superuser = True

    first_job = JobFactory(user_id=first_role_user.user.id,
                           meeting_id=first_role_user.meeting.id)
    second_job = JobFactory(user_id=second_role_user.user.id,
                            meeting_id=first_role_user.meeting.id)

    db.session.add(first_job)
    db.session.add(second_job)
    db.session.commit()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = first_role_user.user.id

        resp = client.get(url_for('meetings.processing_file_list',
                                  meeting_id=meeting.id))
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

    first_job = JobFactory(user_id=first_role_user.user.id,
                           meeting_id=first_role_user.meeting.id)
    second_job = JobFactory(user_id=second_role_user.user.id,
                            meeting_id=first_role_user.meeting.id)

    db.session.add(first_job)
    db.session.add(second_job)
    db.session.commit()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = first_role_user.user.id

        resp = client.get(url_for('meetings.processing_file_list',
                                  meeting_id=meeting.id))
        assert resp.status_code == 200
        html = PyQuery(resp.data)
        assert html('#job-list tbody tr').length == 1


def test_user_without_permissions(app, user):
    role = RoleFactory(permissions=('',))
    role_user = RoleUserMeetingFactory(role=role)

    job = JobFactory(user_id=role_user.user.id,
                     meeting_id=role_user.meeting.id)

    role_user.user.active = False

    db.session.add(job)
    db.session.commit()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id

        resp = client.get(url_for('meetings.processing_file_list',
                                  meeting_id=role_user.meeting.id))
        assert resp.status_code == 403
