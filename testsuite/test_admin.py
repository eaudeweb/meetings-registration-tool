import os

from flask import url_for

from mrt.models import Staff, CategoryDefault
from .factories import StaffFactory, CategoryDefaultFactory, normalize_data

from pyquery import PyQuery
from StringIO import StringIO


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


def test_category_list(app):
    CategoryDefaultFactory()
    CategoryDefaultFactory()

    client = app.test_client()
    with app.test_request_context():
        url = url_for('admin.categories')
        resp = client.get(url)

    table = PyQuery(resp.data)('#categories')
    tbody = table('tbody')
    row_count = len(tbody('tr'))

    assert row_count == 2


def test_category_add_without_file(app):
    data = CategoryDefaultFactory.attributes()
    data = normalize_data(data)
    data['name-english'] = data.pop('name')

    client = app.test_client()
    with app.test_request_context():
        url = url_for('admin.category_edit')
        resp = client.post(url, data=data)

    assert resp.status_code == 302
    assert CategoryDefault.query.count() == 1


def test_category_edit_without_file(app):
    category = CategoryDefaultFactory()
    data = normalize_data(CategoryDefaultFactory.attributes())
    data['name-english'] = 'Comitee'

    client = app.test_client()
    with app.test_request_context():
        url = url_for('admin.category_edit', category_id=category.id)
        resp = client.post(url, data=data)

    assert resp.status_code == 302
    assert CategoryDefault.query.get(category.id).name.english == 'Comitee'


def test_category_delete_without_file(app):
    category = CategoryDefaultFactory()

    client = app.test_client()
    with app.test_request_context():
        url = url_for('admin.category_edit', category_id=category.id)
        resp = client.delete(url)

    assert resp.status_code == 200
    assert CategoryDefault.query.count() == 0


def test_category_add_with_file(app):
    data = CategoryDefaultFactory.attributes()
    data = normalize_data(data)
    data['name-english'] = data.pop('name')
    data['background'] = (StringIO('Test image'), 'image_add.jpg')

    client = app.test_client()
    with app.test_request_context():
        url = url_for('admin.category_edit')
        resp = client.post(url, data=data)

    upload_dest = app.config['UPLOADED_BACKGROUNDS_DEST']

    assert resp.status_code == 302
    assert CategoryDefault.query.count() == 1
    assert os.path.isfile(os.path.join(upload_dest, 'image_add.jpg'))


def test_category_edit_with_file(app):
    category = CategoryDefaultFactory()
    data = normalize_data(CategoryDefaultFactory.attributes())
    data['name-english'] = 'Comitee'
    data['background'] = (StringIO('Test image'), 'image_edit.jpg')

    client = app.test_client()
    with app.test_request_context():
        url = url_for('admin.category_edit', category_id=category.id)
        resp = client.post(url, data=data)

    upload_dest = app.config['UPLOADED_BACKGROUNDS_DEST']
    assert resp.status_code == 302
    assert os.path.isfile(os.path.join(upload_dest, 'image_edit.jpg'))


def test_category_delete_with_file(app):
    category = CategoryDefaultFactory()
    data = normalize_data(CategoryDefaultFactory.attributes())
    data['name-english'] = 'Comitee'
    data['background'] = (StringIO('Test image'), 'image_delete.jpg')

    client = app.test_client()
    with app.test_request_context():
        url = url_for('admin.category_edit', category_id=category.id)
        client.post(url, data=data)
        url = url_for('admin.category_edit', category_id=category.id)
        resp = client.delete(url)

    upload_dest = app.config['UPLOADED_BACKGROUNDS_DEST']
    assert resp.status_code == 200
    assert CategoryDefault.query.count() == 0
    assert not os.path.isfile(os.path.join(upload_dest, 'image_delete.jpg'))
