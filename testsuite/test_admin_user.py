from flask import url_for

from mrt.mail import mail
from .factories import UserFactory, StaffFactory


def test_login_fail_user_inactive(app, user):
    new_user = UserFactory()
    StaffFactory(user=new_user)
    data = UserFactory.attributes()

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
