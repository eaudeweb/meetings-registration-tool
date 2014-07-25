from flask import url_for
from pyquery import PyQuery

from mrt.models import User
from mrt.mail import mail
from .factories import UserFactory


def test_login_succesfull(app):
    UserFactory()
    data = UserFactory.attributes()

    client = app.test_client()
    with app.test_request_context():
        url = url_for('auth.login')
        resp = client.post(url, data=data)

    assert resp.status_code == 302


def test_recover_password(app):
    user = UserFactory()
    data = UserFactory.attributes()

    client = app.test_client()
    with app.test_request_context(), mail.record_messages() as outbox:
        url = url_for('auth.recover')
        resp = client.post(url, data=data)
        assert len(outbox) == 1

    assert resp.status_code == 302
    user = User.query.get(user.id)
    assert user is not None

    data['confirm'] = data['password'] = 'webdeeau'
    with app.test_request_context():
        url = url_for('auth.reset', token=user.recover_token)
        resp = client.post(url, data=data)

    assert user.check_password('webdeeau')


def test_change_password_succesfully(app):
    user = UserFactory()
    data = UserFactory.attributes()
    data['new_password'] = 'webdeeau'
    data['confirm'] = 'webdeeau'

    client = app.test_client()
    with app.test_request_context():
        url = url_for('auth.login')
        resp = client.post(url, data=data)
        url = url_for('auth.change_password')
        resp = client.post(url, data=data)

    assert resp.status_code == 302
    assert user.check_password('webdeeau')


def test_change_password_fail(app):
    UserFactory()
    data = UserFactory.attributes()
    data['new_password'] = 'webdeeau'
    data['confirm'] = 'webeau'

    client = app.test_client()
    with app.test_request_context():
        url = url_for('auth.login')
        resp = client.post(url, data=data)
        data['password'] = 'baddpass'
        url = url_for('auth.change_password')
        resp = client.post(url, data=data)

    errors = PyQuery(resp.data)('.alert-danger')

    assert resp.status_code == 200
    assert len(errors) == 2
