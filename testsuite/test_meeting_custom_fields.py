from flask import url_for
from pyquery import PyQuery
from factory import Sequence

from mrt.models import CustomField
from .factories import CustomFieldFactory, MeetingFactory
from .factories import RoleUserMeetingFactory
from .utils import add_participant_custom_fields


def test_meeting_custom_fields_list(app):
    meeting = MeetingFactory()
    role_user = RoleUserMeetingFactory(meeting=meeting,
                                       role__permissions=('manage_meeting',))
    CustomFieldFactory.create_batch(
        5, meeting=meeting, slug=Sequence(lambda n: 'custom_field_%d' % n))
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        resp = client.get(url_for('meetings.custom_fields',
                                  meeting_id=meeting.id))
        assert resp.status_code == 200
        rows = PyQuery(resp.data)('table tbody tr')
        assert len(rows) == 5


def test_meeting_custom_field_add(app):
    meeting = MeetingFactory()
    role_user = RoleUserMeetingFactory(meeting=meeting,
                                       role__permissions=('manage_meeting',))
    data = CustomFieldFactory.attributes()
    data['label-english'] = data['label'].english
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        resp = client.post(url_for('meetings.custom_field_edit',
                                   meeting_id=meeting.id), data=data)
        assert resp.status_code == 302
        assert CustomField.query.scalar()


def test_meeting_custom_field_add_sort_init(app):
    meeting = MeetingFactory()
    role_user = RoleUserMeetingFactory(meeting=meeting,
                                       role__permissions=('manage_meeting',))
    data = CustomFieldFactory.attributes()
    data['label-english'] = data['label'].english
    client = app.test_client()
    with app.test_request_context():
        add_participant_custom_fields(meeting)
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        max_sort = max([x.sort for x in CustomField.query.all()])
        resp = client.post(url_for('meetings.custom_field_edit',
                                   meeting_id=meeting.id), data=data)
        assert resp.status_code == 302
        new_max_sort = max([x.sort for x in CustomField.query.all()])
        assert new_max_sort == max_sort + 1


def test_meeting_custom_field_edit(app):
    field = CustomFieldFactory()
    role_user = RoleUserMeetingFactory(meeting=field.meeting,
                                       role__permissions=('manage_meeting',))
    data = CustomFieldFactory.attributes()
    data['label-english'] = label = 'Approval'
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        resp = client.post(url_for('meetings.custom_field_edit',
                                   meeting_id=field.meeting.id,
                                   custom_field_id=field.id), data=data)
        assert resp.status_code == 302
        assert field.label.english == label


def test_meeting_custom_field_delete(app):
    field = CustomFieldFactory()
    role_user = RoleUserMeetingFactory(meeting=field.meeting,
                                       role__permissions=('manage_meeting',))
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        resp = client.delete(url_for('meetings.custom_field_edit',
                                     meeting_id=field.meeting.id,
                                     custom_field_id=field.id))
        assert resp.status_code == 200
        assert 'success' in resp.data
        assert not CustomField.query.first()
