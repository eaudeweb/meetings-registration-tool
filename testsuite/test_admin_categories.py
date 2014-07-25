from StringIO import StringIO
from flask import url_for
from pyquery import PyQuery
from py.path import local

from mrt.models import CategoryDefault
from .factories import CategoryDefaultFactory, normalize_data


def test_category_list(app):
    CategoryDefaultFactory.create_batch(5)

    client = app.test_client()
    with app.test_request_context():
        url = url_for('admin.categories')
        resp = client.get(url)

    table = PyQuery(resp.data)('#categories')
    tbody = table('tbody')
    row_count = len(tbody('tr'))

    assert row_count == 5


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
    name = 'Comitee'
    data['name-english'] = name

    client = app.test_client()
    with app.test_request_context():
        url = url_for('admin.category_edit', category_id=category.id)
        resp = client.post(url, data=data)

    assert resp.status_code == 302
    category = CategoryDefault.query.get(category.id)
    assert category is not None
    assert category.name.english == name


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
    filename = 'image_add.jpg'
    data['background'] = (StringIO('Test image'), filename)

    client = app.test_client()
    with app.test_request_context():
        url = url_for('admin.category_edit')
        resp = client.post(url, data=data)

    upload_dir = local(app.config['UPLOADED_BACKGROUNDS_DEST'])
    assert resp.status_code == 302
    assert CategoryDefault.query.count() == 1
    category = CategoryDefault.query.get(1)
    assert category.background == filename
    assert upload_dir.join(filename).check()


def test_category_edit_file_delete(app):
    data = CategoryDefaultFactory.attributes()
    data = normalize_data(data)
    data['name-english'] = data.pop('name')
    filename = 'image_edit_delete.jpg'
    data['background'] = (StringIO('Test image'), filename)

    client = app.test_client()
    with app.test_request_context():
        url = url_for('admin.category_edit')
        resp = client.post(url, data=data)

    upload_dir = local(app.config['UPLOADED_BACKGROUNDS_DEST'])
    assert resp.status_code == 302
    assert CategoryDefault.query.count() == 1
    assert upload_dir.join(filename).check()

    data.pop('background')
    data['background_delete'] = 'y'
    with app.test_request_context():
        url = url_for('admin.category_edit', category_id=1)
        resp = client.post(url, data=data)

    assert resp.status_code == 302
    assert not upload_dir.join(filename).check()


def test_category_edit_with_file(app):
    category = CategoryDefaultFactory()
    data = normalize_data(CategoryDefaultFactory.attributes())
    data['name-english'] = 'Comitee'
    filename = 'image_edit.jpg'
    data['background'] = (StringIO('Test image'), filename)

    client = app.test_client()
    with app.test_request_context():
        url = url_for('admin.category_edit', category_id=category.id)
        resp = client.post(url, data=data)

    upload_dir = local(app.config['UPLOADED_BACKGROUNDS_DEST'])
    assert resp.status_code == 302
    category = CategoryDefault.query.get(category.id)
    assert category is not None
    assert category.background == filename
    assert upload_dir.join(filename).check()


def test_category_delete_with_file(app):
    category = CategoryDefaultFactory()
    data = normalize_data(CategoryDefaultFactory.attributes())
    data['name-english'] = 'Comitee'
    filename = 'image_delete.jpg'
    data['background'] = (StringIO('Test image'), filename)

    client = app.test_client()
    with app.test_request_context():
        url = url_for('admin.category_edit', category_id=category.id)
        client.post(url, data=data)
        url = url_for('admin.category_edit', category_id=category.id)
        resp = client.delete(url)

    upload_dir = local(app.config['UPLOADED_BACKGROUNDS_DEST'])
    assert resp.status_code == 200
    assert CategoryDefault.query.count() == 0
    assert not upload_dir.join(filename).check()
