from flask import url_for
from pyquery import PyQuery

from .factories import MeetingTypeFactory, MeetingFactory
from mrt.models import MeetingType

PERMISSION = ('manage_default', )


def test_default_meeting_types_not_visible(app, user, default_meeting_type):
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.get(url_for('admin.meeting_types'))
        assert resp.status_code == 200
        rows = PyQuery(resp.data)('table#meeting-types tbody tr')
        assert len(rows) == 0


def test_meeting_types_list(app, user, default_meeting_type):
    MeetingTypeFactory.create_batch(3)
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.get(url_for('admin.meeting_types'))
        assert resp.status_code == 200
        rows = PyQuery(resp.data)('table#meeting-types tbody tr')
        assert len(rows) == 3


def test_meeting_type_edit(app, user, default_meeting_type):
    client = app.test_client()
    meeting_type = MeetingTypeFactory()
    data = {'label': 'New label'}
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.meeting_type_edit',
                      meeting_type_slug=meeting_type.slug)
        resp = client.post(url, data=data, follow_redirects=True)
        assert resp.status_code == 200
        alert = PyQuery(resp.data)('.alert-success')
        assert len(alert) == 1
        assert meeting_type.label == data['label']


def test_meeting_type_edit_slug_disabled(app, user, default_meeting_type):
    client = app.test_client()
    meeting_type = MeetingTypeFactory()
    old_slug = meeting_type.slug
    data = {'slug': 'new', 'label': 'New label'}
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.meeting_type_edit',
                      meeting_type_slug=meeting_type.slug)
        resp = client.post(url, data=data, follow_redirects=True)
        assert resp.status_code == 200
        alert = PyQuery(resp.data)('.alert-success')
        assert len(alert) == 1
        assert meeting_type.label == data['label']
        assert meeting_type.slug != data['slug']
        assert meeting_type.slug == old_slug


def test_meeting_type_edit_not_found(app, user, default_meeting_type):
    client = app.test_client()
    data = {'label': 'New label'}
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.meeting_type_edit', meeting_type_slug='new')
        resp = client.post(url, data=data, follow_redirects=True)
        assert resp.status_code == 404


def test_meeting_type_add(app, user, default_meeting_type):
    client = app.test_client()
    data = {'slug': 'new', 'label': 'New label'}
    assert MeetingType.query.count() == 1  # Default meeting type
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.meeting_type_edit')
        resp = client.post(url, data=data, follow_redirects=True)
        assert resp.status_code == 200
        alert = PyQuery(resp.data)('.alert-success')
        assert len(alert) == 1
        assert MeetingType.query.count() == 2


def test_meeting_type_add_existing_slug(app, user, default_meeting_type):
    client = app.test_client()
    data = {'slug': 'def', 'label': 'New default'}
    assert MeetingType.query.count() == 1  # Default meeting type
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.meeting_type_edit')
        resp = client.post(url, data=data, follow_redirects=True)
        assert resp.status_code == 200
        alert = PyQuery(resp.data)('.alert-danger')
        assert len(alert) == 1
        assert MeetingType.query.count() == 1


def test_meeting_type_add_default_fails(app, user, default_meeting_type):
    client = app.test_client()
    data = {'slug': 'df', 'label': 'New default', 'default': True}
    assert MeetingType.query.count() == 1  # Default meeting type
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.meeting_type_edit')
        resp = client.post(url, data=data, follow_redirects=True)
        assert resp.status_code == 200
        alert = PyQuery(resp.data)('.alert-success')
        assert len(alert) == 1
        assert MeetingType.query.count() == 2
        assert MeetingType.query.get(data['slug']).default is False


def test_meeting_type_delete(app, user, default_meeting_type):
    client = app.test_client()
    meeting_type = MeetingTypeFactory()
    assert MeetingType.query.count() == 2
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.meeting_type_edit',
                      meeting_type_slug=meeting_type.slug)
        resp = client.delete(url)
        assert resp.status_code == 200
        assert 'success' in resp.data
        assert MeetingType.query.count() == 1
        assert not MeetingType.query.get(meeting_type.slug)


def test_meeting_type_delete_default(app, user, default_meeting_type):
    client = app.test_client()
    assert MeetingType.query.count() == 1
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.meeting_type_edit', meeting_type_slug='def')
        resp = client.delete(url)
        assert resp.status_code == 403
        assert MeetingType.query.count() == 1


def test_meeting_type_delete_not_found(app, user, default_meeting_type):
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.meeting_type_edit', meeting_type_slug='aaa')
        resp = client.delete(url)
        assert resp.status_code == 404


def test_meeting_type_delete_meeting_associated(app, user,
                                                default_meeting_type):
    client = app.test_client()
    meeting = MeetingFactory()
    assert MeetingType.query.count() == 2
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.meeting_type_edit',
                      meeting_type_slug=meeting.meeting_type.slug)
        resp = client.delete(url)
        assert resp.status_code == 200
        assert 'error' in resp.data
        assert MeetingType.query.count() == 2
