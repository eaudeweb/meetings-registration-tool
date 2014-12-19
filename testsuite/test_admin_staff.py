from flask import url_for
from pyquery import PyQuery

from mrt.models import Staff, RoleUser
from mrt.mail import mail
from .factories import StaffFactory, UserFactory, RoleFactory, RoleUserFactory


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
    role = RoleFactory()
    data['user-email'] = 'test@email.com'
    data['user-is_superuser'] = 'y'
    data['role_id'] = role.id

    client = app.test_client()
    with app.test_request_context(), mail.record_messages() as outbox:
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.staff_edit')
        resp = client.post(url, data=data)
        assert len(outbox) == 1
        assert resp.status_code == 302
        assert Staff.query.count() == 2
        staff = Staff.query.get(2)
        assert staff.user.is_superuser is True
        assert RoleUser.query.filter_by(user=staff.user).count() == 1
        return staff


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
    role = RoleFactory()
    data = StaffFactory.attributes()
    data['user-email'] = new_user.email
    data['role_id'] = role.id

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
    RoleUserFactory(user=staff.user)
    role = RoleFactory()
    data = StaffFactory.attributes()
    data['user-email'] = staff.user.email
    data['user-is_superuser'] = 'y'
    data['title'] = title = 'CEO'
    data['role_id'] = role.id

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


def test_staff_edit_user(app, user):
    staff = StaffFactory()
    RoleUserFactory(user=staff.user)
    role = RoleFactory()
    data = StaffFactory.attributes()
    data['user-email'] = new_email = 'newemail@domain.com'
    data['role_id'] = role.id

    client = app.test_client()
    with app.test_request_context(), mail.record_messages() as outbox:
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.staff_edit', staff_id=staff.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 302
        assert len(outbox) == 0
        assert staff.user.email == new_email


def test_staff_delete(app, user):
    staff = test_staff_add(app, user)
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.staff_edit', staff_id=staff.id)
        resp = client.delete(url)

    assert resp.status_code == 200
    assert Staff.query.count() == 1
    assert RoleUser.query.filter_by(user=staff.user).count() == 0
