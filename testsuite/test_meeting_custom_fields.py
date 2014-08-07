from flask import url_for
from pyquery import PyQuery

from mrt.models import CustomField
from .factories import CustomFieldFactory, MeetingFactory


def test_meeting_custom_fields_list(app):
    meeting = MeetingFactory()
    CustomFieldFactory.create_batch(5, meeting=meeting)
    client = app.test_client()
    with app.test_request_context():
        resp = client.get(url_for('meetings.custom_fields',
                                  meeting_id=meeting.id))
        assert resp.status_code == 200
        rows = PyQuery(resp.data)('table tbody tr')
        assert len(rows) == 5


def test_meeting_custom_field_add(app):
    meeting = MeetingFactory()
    data = CustomFieldFactory.attributes()
    data['label-english'] = data['label'].english
    client = app.test_client()
    with app.test_request_context():
        resp = client.post(url_for('meetings.custom_field_edit',
                                   meeting_id=meeting.id), data=data)
        assert resp.status_code == 302
        assert CustomField.query.scalar()


def test_meeting_custom_field_edit(app):
    field = CustomFieldFactory()
    data = CustomFieldFactory.attributes()
    data['label-english'] = label = 'Approval'
    client = app.test_client()
    with app.test_request_context():
        resp = client.post(url_for('meetings.custom_field_edit',
                                   meeting_id=field.meeting.id,
                                   custom_field_id=field.id), data=data)
        assert resp.status_code == 302
        assert field.label.english == label


def test_meeting_custom_field_delete(app):
    field = CustomFieldFactory()
    client = app.test_client()
    with app.test_request_context():
        resp = client.delete(url_for('meetings.custom_field_edit',
                                     meeting_id=field.meeting.id,
                                     custom_field_id=field.id))
        assert resp.status_code == 200
        assert 'success' in resp.data
        assert not CustomField.query.first()
