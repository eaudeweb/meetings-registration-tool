from uuid import uuid4
from flask import url_for
from pyquery import PyQuery

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
        resp = client.post(url_for('auth.recover'), data=data)
        assert resp.status_code == 302
        assert len(outbox) == 1

    data['confirm'] = data['password'] = 'webdeeau'
    with app.test_request_context():
        url = url_for('auth.reset', token=user.recover_token)
        resp = client.post(url, data=data)
        assert resp.status_code == 302

    assert user.check_password('webdeeau')


def test_change_password_succesfully(app):
    user, data = UserFactory(), UserFactory.attributes()
    data['new_password'] = data['confirm'] = passwd = str(uuid4())

    client = app.test_client()
    with app.test_request_context():
        client.post(url_for('auth.login'), data=data)
        resp = client.post(url_for('auth.change_password'), data=data)
        assert resp.status_code == 302

    assert user.check_password(passwd)


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
