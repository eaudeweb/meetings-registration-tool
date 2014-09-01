from flask import url_for
from pyquery import PyQuery
from werkzeug.datastructures import MultiDict

from mrt.models import Role
from .factories import RoleFactory, RoleUserFactory


PERMISSION = ('manage_role', )


def test_role_list(app):
    role_user = RoleUserFactory(role__permissions=PERMISSION)
    RoleFactory.create_batch(5)
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        resp = client.get(url_for('admin.roles'))
        assert resp.status_code == 200
        rows = PyQuery(resp.data)('table tbody tr')
        assert len(rows) == 6


def test_role_add(app):
    role_user = RoleUserFactory(role__permissions=PERMISSION)
    data = MultiDict(RoleFactory.attributes())
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        resp = client.post(url_for('admin.role_edit'), data=data)
        assert resp.status_code == 302
        assert Role.query.count() == 2


def test_role_edit(app):
    role_user = RoleUserFactory(role__permissions=PERMISSION)
    role = RoleFactory()
    data = MultiDict(RoleFactory.attributes())
    data['name'] = name = 'Admin'
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        resp = client.post(url_for('admin.role_edit', role_id=2), data=data)
        assert resp.status_code == 302
        assert role.name == name


def test_role_delete_successfuly(app):
    role_user = RoleUserFactory(role__permissions=PERMISSION)
    RoleFactory()
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        resp = client.delete(url_for('admin.role_edit', role_id=2))
        assert resp.status_code == 200
        assert 'success' in resp.data
        assert Role.query.count() == 1


def test_role_delete_fail(app):
    role_user = RoleUserFactory(role__permissions=PERMISSION)
    RoleUserFactory(user__email='test@email.com')
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        resp = client.delete(url_for('admin.role_edit', role_id=2))
        assert resp.status_code == 200
        assert 'error' in resp.data
        assert Role.query.count() == 2
