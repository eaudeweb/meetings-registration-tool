from flask import url_for
from pyquery import PyQuery
from werkzeug.datastructures import MultiDict

from mrt.models import Role
from .factories import RoleFactory, RoleUserMeetingFactory


def test_role_list(app, user):
    RoleFactory.create_batch(5)
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.get(url_for('admin.roles'))
        assert resp.status_code == 200
        rows = PyQuery(resp.data)('table tbody tr')
        assert len(rows) == 5


def test_role_add(app, user):
    data = MultiDict(RoleFactory.attributes())
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('admin.role_edit'), data=data)
        assert resp.status_code == 302
        assert Role.query.count() == 1


def test_role_edit(app, user):
    role = RoleFactory()
    data = MultiDict(RoleFactory.attributes())
    data['name'] = name = 'Admin'
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('admin.role_edit', role_id=1), data=data)
        assert resp.status_code == 302
        assert role.name == name


def test_role_delete_successfuly(app, user):
    RoleFactory()
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.delete(url_for('admin.role_edit', role_id=1))
        assert resp.status_code == 200
        assert 'success' in resp.data
        assert Role.query.count() == 0


def test_role_delete_fail(app, user):
    RoleUserMeetingFactory(user__email='test@email.com')
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.delete(url_for('admin.role_edit', role_id=1))
        assert resp.status_code == 200
        assert 'error' in resp.data
        assert Role.query.count() == 1
