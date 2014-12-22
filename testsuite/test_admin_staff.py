from flask import url_for
from pyquery import PyQuery

from mrt.models import Staff
from mrt.mail import mail
from .factories import StaffFactory, UserFactory

PERMISSION = ('manage_staff', )


def test_staff_list(app, user):
    StaffFactory(user__email='test@email.com')
    StaffFactory(user__email='another_test@email.com')

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.staff')
        resp = client.get(url)

        table = PyQuery(resp.data)('#staff')
        tbody = table('tbody')
        row_count = len(tbody('tr'))
        assert row_count == 3


def test_staff_add(app, user):
    data = StaffFactory.attributes()
    data['user-email'] = 'test@email.com'
    data['user-is_superuser'] = 'y'

    client = app.test_client()
    with app.test_request_context(), mail.record_messages() as outbox:
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.staff_edit')
        resp = client.post(url, data=data)
        assert len(outbox) == 1
        assert resp.status_code == 302
        assert Staff.query.count() == 2
        assert Staff.query.get(2).user.is_superuser is True


def test_staff_add_fail_with_multiple_emails(app, user):
    data = StaffFactory.attributes()
    data['user-email'] = 'test@email.com , test@test.com'
    data['user-is_superuser'] = 'y'

    client = app.test_client()
    with app.test_request_context(), mail.record_messages() as outbox:
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.staff_edit')
        resp = client.post(url, data=data)
        assert len(outbox) == 0
        assert resp.status_code == 200
        assert Staff.query.count() == 1


def test_staff_add_with_existing_user(app, user):
    new_user = UserFactory(email='test@email.com')
    data = StaffFactory.attributes()
    data['user-email'] = new_user.email

    client = app.test_client()
    with app.test_request_context(), mail.record_messages() as outbox:
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.staff_edit')
        resp = client.post(url, data=data)
        assert len(outbox) == 0
        assert resp.status_code == 302
        assert Staff.query.count() == 2


def test_staff_add_fail_with_existing_staff(app, user):
    staff = StaffFactory(user__email='test@email.com')
    data = StaffFactory.attributes()
    data['user-email'] = staff.user.email

    client = app.test_client()
    with app.test_request_context(), mail.record_messages() as outbox:
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.staff_edit')
        resp = client.post(url, data=data)
        assert len(outbox) == 0
        assert resp.status_code == 200
        assert Staff.query.count() == 2


def test_staff_edit(app, user):
    staff = StaffFactory()
    data = StaffFactory.attributes()
    data['user-email'] = staff.user.email
    data['user-is_superuser'] = 'y'
    data['title'] = title = 'CEO'

    client = app.test_client()
    with app.test_request_context(), mail.record_messages() as outbox:
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.staff_edit', staff_id=staff.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 302
        assert len(outbox) == 0
        assert staff.title == title
        assert staff.user.is_superuser is True


def test_staff_delete(app, user):
    staff = StaffFactory()
    assert Staff.query.count() == 2
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.staff_edit', staff_id=staff.id)
        resp = client.delete(url)

    assert resp.status_code == 200
    assert Staff.query.count() == 1


def test_revoke_superuser(app, user):
    data = StaffFactory.attributes()
    data['user-email'] = data.pop('user')
    data['user-is_superuser'] = ''

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.staff_edit', staff_id=user.staff.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 302
        assert user.is_superuser


def test_enable_superuser(app):
    staff = StaffFactory(user__is_superuser=False)
    data = StaffFactory.attributes()
    data['user-email'] = staff.user.email
    data['user-is_superuser'] = 'y'

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = staff.user.id
        url = url_for('admin.staff_edit', staff_id=staff.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 403
        assert not staff.user.is_superuser


def test_enable_superuser_for_other_user(app, user):
    staff = StaffFactory()
    data = StaffFactory.attributes()
    data['user-email'] = data.pop('user')
    data['user-is_superuser'] = 'y'

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.staff_edit', staff_id=staff.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 302
        assert staff.user.is_superuser


def test_disable_superuser_for_other_user(app, user):
    staff = StaffFactory(user__is_superuser=True)
    data = StaffFactory.attributes()
    data['user-email'] = staff.user.email
    data['user-is_superuser'] = ''

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.staff_edit', staff_id=staff.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 302
        assert not staff.user.is_superuser
