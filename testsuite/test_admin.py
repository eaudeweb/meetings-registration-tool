from flask import url_for

from mrt.models import Staff
from .factories import StaffFactory

from pyquery import PyQuery


def test_staff_list(app):
    StaffFactory()
    StaffFactory(user__email='jeandoe@eaudeweb.ro')

    client = app.test_client()
    with app.test_request_context():
        url = url_for('admin.staff')
        resp = client.get(url)

    table = PyQuery(resp.data)('#staff')
    tbody = table('tbody')
    row_count = len(tbody('tr'))

    assert row_count == 2


def test_staff_add(app):
    data = StaffFactory.attributes()
    data['user-email'] = data['user']

    client = app.test_client()
    with app.test_request_context():
        url = url_for('admin.staff_edit')
        resp = client.post(url, data=data)

    assert resp.status_code == 302
    assert Staff.query.count() == 1


def test_staff_edit(app):
    staff = StaffFactory()
    data = StaffFactory.attributes()
    data['user-email'] = data['user']
    data['title'] = 'CEO'

    client = app.test_client()
    with app.test_request_context():
        url = url_for('admin.staff_edit', staff_id=staff.id)
        resp = client.post(url, data=data)

    assert resp.status_code == 302
    assert Staff.query.get(staff.id).title == 'CEO'


def test_staff_delete(app):
    staff = StaffFactory()

    client = app.test_client()
    with app.test_request_context():
        url = url_for('admin.staff_edit', staff_id=staff.id)
        resp = client.delete(url)

    assert resp.status_code == 200
    assert Staff.query.count() == 0
