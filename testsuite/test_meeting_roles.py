from flask import url_for
from pyquery import PyQuery

from mrt.models import RoleUser
from .factories import RoleUserMeetingFactory, MeetingFactory
from .factories import RoleUserFactory, StaffFactory, RoleFactory


def test_meeting_roles_list(app):
    role = RoleUserMeetingFactory()
    client = app.test_client()
    with app.test_request_context():
        resp = client.get(url_for('meetings.roles',
                                  meeting_id=role.meeting.id))
        assert resp.status_code == 200
        rows = PyQuery(resp.data)('table tbody tr')
        assert len(rows) == 1


def test_meeting_role_add(app):
    meeting = MeetingFactory()
    staff = StaffFactory()
    role_user = RoleUserFactory(user=staff.user)
    data = {
        'role_id': role_user.role.id,
        'user_id': staff.user.id
    }
    client = app.test_client()
    with app.test_request_context():
        resp = client.post(url_for('meetings.role_user_edit',
                                   meeting_id=meeting.id), data=data)
        assert resp.status_code == 302
        assert RoleUser.query.filter_by(meeting=meeting).scalar()


def test_meeting_role_edit(app):
    staff = StaffFactory()
    role_user = RoleUserMeetingFactory(user=staff.user)
    new_role = RoleFactory(name='Inspector')
    data = {
        'role_id': new_role.id,
        'user_id': role_user.user.id
    }
    client = app.test_client()
    with app.test_request_context():
        resp = client.post(url_for('meetings.role_user_edit',
                                   meeting_id=role_user.meeting.id,
                                   role_user_id=role_user.id), data=data)
        assert resp.status_code == 302
        assert role_user.role == new_role


def test_meeting_role_delete(app):
    role_user = RoleUserMeetingFactory()
    client = app.test_client()
    with app.test_request_context():
        resp = client.delete(url_for('meetings.role_user_edit',
                                     meeting_id=role_user.meeting.id,
                                     role_user_id=role_user.id))
        assert resp.status_code == 200
        assert 'success' in resp.data
        assert not RoleUser.query.filter_by(meeting=role_user.meeting).first()
