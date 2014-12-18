from flask import url_for
from pyquery import PyQuery

from mrt.models import RoleUser
from .factories import RoleUserMeetingFactory, MeetingFactory
from .factories import StaffFactory, RoleFactory


def test_meeting_roles_list(app, user):
    role = RoleUserMeetingFactory(user__email='test@email.com')
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.get(url_for('meetings.roles',
                                  meeting_id=role.meeting.id))
        assert resp.status_code == 200
        rows = PyQuery(resp.data)('table tbody tr')
        assert len(rows) == 1


def test_meeting_role_add(app, user):
    role = RoleFactory()
    meeting = MeetingFactory()
    staff = StaffFactory(user__email='test@email.com')
    data = {
        'role_id': role.id,
        'user_id': staff.user.id
    }
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('meetings.role_user_edit',
                                   meeting_id=meeting.id), data=data)
        assert resp.status_code == 302
        assert RoleUser.query.filter_by(meeting=meeting).scalar()


def test_meeting_role_edit(app, user):
    staff = StaffFactory(user__email='test@email.com')
    role_user = RoleUserMeetingFactory(staff=staff, user=staff.user)
    new_role = RoleFactory(name='Inspector')
    data = {
        'role_id': new_role.id,
        'user_id': role_user.user.id
    }
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('meetings.role_user_edit',
                                   meeting_id=role_user.meeting.id,
                                   role_user_id=role_user.id), data=data)
        assert resp.status_code == 302
        assert role_user.role == new_role


def test_meeting_role_delete(app, user):
    role = RoleUserMeetingFactory(user__email='test@email.com')
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.delete(url_for('meetings.role_user_edit',
                                     meeting_id=role.meeting.id,
                                     role_user_id=role.id))
        assert resp.status_code == 200
        assert 'success' in resp.data
        assert not RoleUser.query.filter_by(meeting=role.meeting).first()
