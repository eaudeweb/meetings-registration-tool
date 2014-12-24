from StringIO import StringIO
from flask import url_for
from pyquery import PyQuery
from py.path import local

from mrt.models import CategoryDefault
from .factories import CategoryDefaultFactory, normalize_data
from .factories import MeetingTypeFactory


def test_category_list(app, user):
    meeting_type = MeetingTypeFactory()
    CategoryDefaultFactory.create_batch(5, meeting_types=[meeting_type])
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.get(url_for('admin.categories'))
        rows = PyQuery(resp.data)('#categories tbody tr')
        assert len(rows) == 5


def test_category_add_without_file(app, user):
    data = CategoryDefaultFactory.attributes()
    data = normalize_data(data)
    data['title-english'] = data.pop('title')

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.category_edit')
        resp = client.post(url, data=data)
        assert resp.status_code == 302
        assert CategoryDefault.query.count() == 1


def test_category_add_with_same_title_fails(app, user):
    category = CategoryDefaultFactory()
    data = normalize_data(CategoryDefaultFactory.attributes())
    data['title-english'] = category.title.english
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('admin.category_edit'), data=data)
        assert resp.status_code == 200
        assert CategoryDefault.query.count() == 1


def test_category_edit_without_file(app, user):
    category = CategoryDefaultFactory()
    data = normalize_data(CategoryDefaultFactory.attributes())
    data['title-english'] = 'Comitee'

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.category_edit', category_id=category.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 302
        assert category.title.english == data['title-english']


def test_category_delete_without_file(app, user):
    category = CategoryDefaultFactory()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.category_edit', category_id=category.id)
        resp = client.delete(url)
        assert resp.status_code == 200
        assert CategoryDefault.query.count() == 0


def test_category_add_with_file(app, user):
    data = CategoryDefaultFactory.attributes()
    data = normalize_data(data)
    data['title-english'] = data.pop('title')
    filename = 'image_add.jpg'
    data['background'] = (StringIO('Test image'), filename)
    upload_dir = local(app.config['UPLOADED_BACKGROUNDS_DEST'])

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.category_edit')
        resp = client.post(url, data=data)
        assert resp.status_code == 302

        category = CategoryDefault.query.get(1)
        assert category.background != filename
        assert upload_dir.join(category.background).check()


def test_category_edit_file_delete(app, user):
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
            sess['user_id'] = user.id
        url = url_for('admin.category_edit', category_id=1)
        resp = client.post(url, data=data)
        assert resp.status_code == 302
        assert category.background is None
        assert not upload_dir.join(filename).check()


def test_category_edit_with_file(app, user):
    category = CategoryDefaultFactory()
    data = normalize_data(CategoryDefaultFactory.attributes())
    data['title-english'] = 'Comitee'
    filename = 'image_edit.jpg'
    data['background'] = (StringIO('Test image'), filename)
    upload_dir = local(app.config['UPLOADED_BACKGROUNDS_DEST'])

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.category_edit', category_id=category.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 302
        assert category is not None
        assert category.background != filename
        assert upload_dir.join(category.background).check()


def test_category_delete_with_file(app, user):
    category = CategoryDefaultFactory()
    category.background = filename = 'image_edit.jpg'
    upload_dir = local(app.config['UPLOADED_BACKGROUNDS_DEST'])
    upload_dir.ensure(filename)

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.category_edit', category_id=1)
        resp = client.delete(url)
        assert resp.status_code == 200
        assert CategoryDefault.query.count() == 0
        assert not upload_dir.join(category.background).check()


def test_add_category_with_meeting_types(app, user):
    meeting_types = MeetingTypeFactory.create_batch(2)
    data = normalize_data(CategoryDefaultFactory.attributes())
    data['title-english'] = 'Comitee'
    data['meeting_type_slugs'] = [m.slug for m in meeting_types]

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.category_edit')
        resp = client.post(url, data=data)
        assert resp.status_code == 302
        assert CategoryDefault.query.count() == 1
        category = CategoryDefault.query.first()
        assert set(category.meeting_types) == set(meeting_types)


def test_edit_category_add_meeting_types(app, user):
    category = CategoryDefaultFactory()
    meeting_type = MeetingTypeFactory()
    data = normalize_data(CategoryDefaultFactory.attributes())
    data['title-english'] = 'Comitee'
    data['meeting_type_slugs'] = [meeting_type.slug]

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.category_edit', category_id=category.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 302
        assert category.meeting_types == [meeting_type]


def test_edit_category_delete_meeting_types(app, user):
    meeting_types = MeetingTypeFactory.create_batch(2)
    category = CategoryDefaultFactory(meeting_types=meeting_types)
    data = normalize_data(CategoryDefaultFactory.attributes())
    data['title-english'] = 'Comitee'
    data['meeting_type_slugs'] = []
    assert category.meeting_types == meeting_types

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.category_edit', category_id=category.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 302
        assert category.meeting_types == []


def test_edit_category_add_meeting_types_default(app, user,
                                                 default_meeting_type):
    category = CategoryDefaultFactory()
    MeetingTypeFactory.create_batch(3)
    data = normalize_data(CategoryDefaultFactory.attributes())
    data['title-english'] = 'Comitee'
    data['meeting_type_slugs'] = ['def']

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.category_edit', category_id=category.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 200
        errors = PyQuery(resp.data)('.text-danger small')
        assert len(errors) == 1
        assert errors[0].text == "'def' is not a valid choice for this field"
        assert category.meeting_types == []
