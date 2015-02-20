from flask import url_for
from pyquery import PyQuery

from mrt.models import CustomField
from .factories import MeetingTypeFactory, CustomFieldFactory


def test_default_custom_field_list(app, user):
    CustomFieldFactory.create_batch(5, meeting=None)
    CustomFieldFactory.create_batch(3, meeting=None,
                                    custom_field_type=CustomField.MEDIA)
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.get(url_for('admin.custom_fields'))
        rows = PyQuery(resp.data)('#participant table tbody tr')
        assert len(rows) == 5
        rows = PyQuery(resp.data)('#media table tbody tr')
        assert len(rows) == 3


def test_default_custom_field_add(app, user):
    data = CustomFieldFactory.attributes()
    data.pop('meeting')
    data['label-english'] = data['label'].english
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('admin.custom_field_edit',
                                   custom_field_type=CustomField.PARTICIPANT),
                           data=data)
        assert resp.status_code == 302
        assert CustomField.query.filter_by(meeting=None).count() == 1
        custom_field = CustomField.query.get(1)
        assert custom_field.custom_field_type.code == CustomField.PARTICIPANT


def test_default_custom_field_add_with_meeting_types(app, user):
    meeting_types = MeetingTypeFactory.create_batch(2)
    data = CustomFieldFactory.attributes()
    data.pop('meeting')
    data['label-english'] = data['label'].english
    data['meeting_type_slugs'] = [m.slug for m in meeting_types]
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('admin.custom_field_edit',
                                   custom_field_type=CustomField.PARTICIPANT),
                           data=data)
        assert resp.status_code == 302
        assert CustomField.query.filter_by(meeting=None).count() == 1
        custom_field = CustomField.query.get(1)
        assert set(custom_field.meeting_types) == set(meeting_types)


def test_default_custom_field_edit(app, user):
    field = CustomFieldFactory(meeting=None)
    data = CustomFieldFactory.attributes()
    data.pop('meeting')
    data['label-english'] = field.label.english
    data.pop('required')
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        assert field.required is True
        resp = client.post(url_for('admin.custom_field_edit',
                                   custom_field_id=field.id), data=data)
        assert resp.status_code == 302
        assert field.required is False


def test_default_custom_field_delete(app, user):
    field = CustomFieldFactory(meeting=None)
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.delete(url_for('admin.custom_field_edit',
                                     custom_field_id=field.id))
        assert resp.status_code == 200
        assert 'success' in resp.data
        assert not CustomField.query.first()
