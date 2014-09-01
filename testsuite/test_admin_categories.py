from StringIO import StringIO
from flask import url_for
from pyquery import PyQuery
from py.path import local

from mrt.models import CategoryDefault
from .factories import CategoryDefaultFactory, normalize_data, RoleUserFactory


PERMISSION = ('manage_category', )


def test_category_list(app):
    role_user = RoleUserFactory(role__permissions=PERMISSION)
    CategoryDefaultFactory.create_batch(5)
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        resp = client.get(url_for('admin.categories'))
        rows = PyQuery(resp.data)('#categories tbody tr')
        assert len(rows) == 5


def test_category_add_without_file(app):
    role_user = RoleUserFactory(role__permissions=PERMISSION)
    data = CategoryDefaultFactory.attributes()
    data = normalize_data(data)
    data['title-english'] = data.pop('title')

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        url = url_for('admin.category_edit')
        resp = client.post(url, data=data)
        assert resp.status_code == 302
        assert CategoryDefault.query.count() == 1


def test_category_edit_without_file(app):
    role_user = RoleUserFactory(role__permissions=PERMISSION)
    category = CategoryDefaultFactory()
    data = normalize_data(CategoryDefaultFactory.attributes())
    data['title-english'] = 'Comitee'

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        url = url_for('admin.category_edit', category_id=category.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 302
        assert category.title.english == data['title-english']


def test_category_delete_without_file(app):
    role_user = RoleUserFactory(role__permissions=PERMISSION)
    category = CategoryDefaultFactory()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        url = url_for('admin.category_edit', category_id=category.id)
        resp = client.delete(url)
        assert resp.status_code == 200
        assert CategoryDefault.query.count() == 0


def test_category_add_with_file(app):
    role_user = RoleUserFactory(role__permissions=PERMISSION)
    data = CategoryDefaultFactory.attributes()
    data = normalize_data(data)
    data['title-english'] = data.pop('title')
    filename = 'image_add.jpg'
    data['background'] = (StringIO('Test image'), filename)
    upload_dir = local(app.config['UPLOADED_BACKGROUNDS_DEST'])

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        url = url_for('admin.category_edit')
        resp = client.post(url, data=data)
        assert resp.status_code == 302

        category = CategoryDefault.query.get(1)
        assert category.background != filename
        assert upload_dir.join(category.background).check()


def test_category_edit_file_delete(app):
    role_user = RoleUserFactory(role__permissions=PERMISSION)
    category = CategoryDefaultFactory()
    category.background = filename = 'image_edit.jpg'
    upload_dir = local(app.config['UPLOADED_BACKGROUNDS_DEST'])
    upload_dir.ensure(filename)

    data = normalize_data(CategoryDefaultFactory.attributes())
    data['title-english'] = data.pop('title')
    data['background_delete'] = 'y'

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        url = url_for('admin.category_edit', category_id=1)
        resp = client.post(url, data=data)
        assert resp.status_code == 302
        assert category.background is None
        assert not upload_dir.join(filename).check()


def test_category_edit_with_file(app):
    role_user = RoleUserFactory(role__permissions=PERMISSION)
    category = CategoryDefaultFactory()
    data = normalize_data(CategoryDefaultFactory.attributes())
    data['title-english'] = 'Comitee'
    filename = 'image_edit.jpg'
    data['background'] = (StringIO('Test image'), filename)
    upload_dir = local(app.config['UPLOADED_BACKGROUNDS_DEST'])

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        url = url_for('admin.category_edit', category_id=category.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 302
        assert category is not None
        assert category.background != filename
        assert upload_dir.join(category.background).check()


def test_category_delete_with_file(app):
    role_user = RoleUserFactory(role__permissions=PERMISSION)
    category = CategoryDefaultFactory()
    category.background = filename = 'image_edit.jpg'
    upload_dir = local(app.config['UPLOADED_BACKGROUNDS_DEST'])
    upload_dir.ensure(filename)

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        url = url_for('admin.category_edit', category_id=1)
        resp = client.delete(url)
        assert resp.status_code == 200
        assert CategoryDefault.query.count() == 0
        assert not upload_dir.join(category.background).check()
