from flask import url_for
from pyquery import PyQuery

from mrt.mail import mail
from .factories import UserFactory, StaffFactory, ParticipantUserFactory


def test_admin_list(app, user):
    UserFactory.create_batch(30)
    ParticipantUserFactory.create_batch(30)
    TOTAL_USERS = 30 + 30 + 1

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.get(url_for('admin.users'))
        assert resp.status_code == 200
        users = PyQuery(resp.data)('#users tbody tr')
        assert len(users) == TOTAL_USERS


def test_admin_list_user_search(app, user):
    UserFactory()
    UserFactory(email='user@email.com')
    UserFactory(email='user@email.ro')

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.get(url_for('admin.users', search='user'))
        assert resp.status_code == 200
        users = PyQuery(resp.data)('#users tbody tr')
        assert len(users) == 2


def test_login_fail_user_inactive(app, user):
    new_user = UserFactory()
    StaffFactory(user=new_user)
    data = UserFactory.attributes()
    data['email'] = new_user.email

    user_client = app.test_client()
    with app.test_request_context():
        resp = user_client.post(url_for('auth.login'), data=data)
        assert resp.status_code == 302

    admin_client = app.test_client()
    with app.test_request_context():
        with admin_client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = admin_client.post(url_for('admin.user_toggle',
                                         user_id=new_user.id))
        assert resp.status_code == 200

    with app.test_request_context():
        resp = user_client.post(url_for('auth.login'), data=data)
        assert resp.status_code == 200


def test_change_user_password_successfully(app, user):
    new_user = UserFactory()
    data = {
        'email': new_user.email
    }

    client = app.test_client()
    with app.test_request_context(), mail.record_messages() as outbox:
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('admin.user_edit', user_id=new_user.id),
                           data=data)
        assert resp.status_code == 200
        assert 'success' in resp.data
        assert len(outbox) == 1


def test_user_disable_fail_on_own_user(app, user):

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('admin.user_toggle', user_id=user.id))
        assert resp.status_code == 400
        assert user.active is True
