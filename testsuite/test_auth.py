from uuid import uuid4
from flask import url_for
from pyquery import PyQuery

from mrt.mail import mail
from .factories import UserFactory, StaffFactory


def test_login_for_staff_succesfull(app):
    user = UserFactory()
    StaffFactory(user=user)
    data = UserFactory.attributes()
    data['email'] = user.email

    client = app.test_client()
    with app.test_request_context():
        url = url_for('auth.login')
        resp = client.post(url, data=data)

    assert resp.status_code == 302


def test_login_failed_for_users_failed(app):
    UserFactory()
    data = UserFactory.attributes()
    client = app.test_client()
    with app.test_request_context():
        url = url_for('auth.login')
        resp = client.post(url, data=data)

    assert resp.status_code == 200


def test_recover_password(app):
    user = UserFactory()
    data = UserFactory.attributes()
    data['email'] = user.email

    client = app.test_client()
    with app.test_request_context(), mail.record_messages() as outbox:
        resp = client.post(url_for('auth.recover'), data=data)
        assert resp.status_code == 302
        assert len(outbox) == 1

    passwd = str(uuid4())
    data['confirm'] = data['password'] = passwd
    with app.test_request_context():
        url = url_for('auth.reset', token=user.recover_token)
        resp = client.post(url, data=data)
        assert resp.status_code == 302

    assert user.check_password(passwd)


def test_recover_password_fail_after_using_token(app):
    user = UserFactory()
    StaffFactory(user=user)
    data = UserFactory.attributes()
    data['email'] = user.email

    client = app.test_client()
    with app.test_request_context(), mail.record_messages() as outbox:
        resp = client.post(url_for('auth.recover'), data=data)
        assert resp.status_code == 302
        assert len(outbox) == 1

    passwd = str(uuid4())
    data['confirm'] = data['password'] = passwd
    with app.test_request_context():
        url = url_for('auth.reset', token=user.recover_token)
        resp = client.post(url, data=data)
        assert resp.status_code == 302
        resp = client.post(url, data=data, follow_redirects=True)

    errors = PyQuery(resp.data)('.alert-danger')

    assert resp.status_code == 200
    assert len(errors) == 1


def test_change_password_succesfully(app):
    user, data = UserFactory(), UserFactory.attributes()
    data['new_password'] = data['confirm'] = passwd = str(uuid4())

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        client.post(url_for('auth.login'), data=data)
        resp = client.post(url_for('auth.change_password'), data=data)
        assert resp.status_code == 302

    assert user.check_password(passwd)


def test_change_password_fail(app):
    user = UserFactory()
    data = UserFactory.attributes()
    data['new_password'] = data['confirm'] = 'webdeeau'

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        client.post(url_for('auth.login'), data=data)
        data['password'] = 'baddpass'
        resp = client.post(url_for('auth.change_password'), data=data)
        assert resp.status_code == 200
        assert len(PyQuery(resp.data)('.alert-danger')) == 1
