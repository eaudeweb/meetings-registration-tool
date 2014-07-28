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
        resp = client.get(url_for('admin.categories'))
        rows = PyQuery(resp.data)('#categories tbody tr')
        assert len(rows) == 5


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
        assert category.name.english == data['name-english']


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
    upload_dir = local(app.config['UPLOADED_BACKGROUNDS_DEST'])

    client = app.test_client()
    with app.test_request_context():
        url = url_for('admin.category_edit')
        resp = client.post(url, data=data)
        assert resp.status_code == 302

        category = CategoryDefault.query.get(1)
        assert category.background != filename
        assert upload_dir.join(category.background).check()


def test_category_edit_file_delete(app):
    category = CategoryDefaultFactory()
    category.background = filename = 'image_edit.jpg'
    upload_dir = local(app.config['UPLOADED_BACKGROUNDS_DEST'])
    upload_dir.ensure(filename)

    data = normalize_data(CategoryDefaultFactory.attributes())
    data['name-english'] = data.pop('name')
    data['background_delete'] = 'y'

    client = app.test_client()
    with app.test_request_context():
        url = url_for('admin.category_edit', category_id=1)
        resp = client.post(url, data=data)
        assert resp.status_code == 302
        assert category.background is None
        assert not upload_dir.join(filename).check()


def test_category_edit_with_file(app):
    category = CategoryDefaultFactory()
    data = normalize_data(CategoryDefaultFactory.attributes())
    data['name-english'] = 'Comitee'
    filename = 'image_edit.jpg'
    data['background'] = (StringIO('Test image'), filename)
    upload_dir = local(app.config['UPLOADED_BACKGROUNDS_DEST'])

    client = app.test_client()
    with app.test_request_context():
        url = url_for('admin.category_edit', category_id=category.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 302
        assert category is not None
        assert category.background != filename
        assert upload_dir.join(category.background).check()


def test_category_delete_with_file(app):
    category = CategoryDefaultFactory()
    category.background = filename = 'image_edit.jpg'
    upload_dir = local(app.config['UPLOADED_BACKGROUNDS_DEST'])
    upload_dir.ensure(filename)

    client = app.test_client()
    with app.test_request_context():
        url = url_for('admin.category_edit', category_id=1)
        resp = client.delete(url)
        assert resp.status_code == 200
        assert CategoryDefault.query.count() == 0
        assert not upload_dir.join(category.background).check()
