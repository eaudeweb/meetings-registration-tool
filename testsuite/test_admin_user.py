from flask import url_for

from .factories import UserFactory, RoleUserFactory


def test_login_fail_user_inactive(app):
    admin = RoleUserFactory(user__email='admin@eaudeweb.ro',
                            role__permissions=('manage_default',))
    user = UserFactory()
    data = UserFactory.attributes()

    user_client = app.test_client()
    with app.test_request_context():
        resp = user_client.post(url_for('auth.login'), data=data)
        assert resp.status_code == 302

    admin_client = app.test_client()
    with app.test_request_context():
        with admin_client.session_transaction() as sess:
            sess['user_id'] = admin.user.id
        resp = admin_client.post(url_for('admin.user_toggle', user_id=user.id))
        assert resp.status_code == 200

    with app.test_request_context():
        resp = user_client.post(url_for('auth.login'), data=data)
        assert resp.status_code == 200


def test_change_user_password_successfully(app):
    admin = RoleUserFactory(user__email='admin@eaudeweb.ro',
                            role__permissions=('manage_default',))
    user = UserFactory()
    data = {
        'new_password': 'testpass',
        'confirm': 'testpass'
    }

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = admin.user.id
        resp = client.post(url_for('admin.user_edit', user_id=user.id),
                           data=data)
        assert resp.status_code == 200
        assert 'success' in resp.data


def test_change_user_password_fail(app):
    admin = RoleUserFactory(user__email='admin@eaudeweb.ro',
                            role__permissions=('manage_default',))
    user = UserFactory()
    data = {
        'new_password': 'testpass',
        'confirm': 'passtest'
    }

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = admin.user.id
        resp = client.post(url_for('admin.user_edit', user_id=user.id),
                           data=data)
        assert resp.status_code == 200
        assert 'error' in resp.data
