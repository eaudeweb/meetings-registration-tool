from flask import url_for
from pyquery import PyQuery
from factory import Sequence

from mrt.models import CustomField, Meeting
from .factories import CustomFieldFactory, MeetingFactory, normalize_data
from .factories import RoleUserMeetingFactory, RoleUserFactory, StaffFactory
from .factories import MeetingTypeFactory
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
        assert CustomField.query.count() == 1
        custom_field = CustomField.query.get(1)
        assert custom_field.custom_field_type.code == CustomField.PARTICIPANT


def test_meeting_custom_field_add_for_media_participant(app):
    meeting = MeetingFactory()
    role_user = RoleUserMeetingFactory(meeting=meeting,
                                       role__permissions=('manage_meeting',))
    data = CustomFieldFactory.attributes()
    data['label-english'] = data['label'].english
    data['custom_field_type'] = CustomField.MEDIA
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        resp = client.post(url_for('meetings.custom_field_edit',
                                   meeting_id=meeting.id), data=data)
        assert resp.status_code == 302
        assert CustomField.query.count() == 1
        custom_field = CustomField.query.get(1)
        assert custom_field.custom_field_type.code == CustomField.MEDIA


def test_meeting_custom_field_add_with_same_slug_and_different_type(app):
    meeting = MeetingFactory()
    role_user = RoleUserMeetingFactory(meeting=meeting,
                                       role__permissions=('manage_meeting',))
    participant_field = CustomFieldFactory(meeting=meeting)
    data = CustomFieldFactory.attributes()
    data['label-english'] = data['label'].english
    data['custom_field_type'] = CustomField.MEDIA
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        resp = client.post(url_for('meetings.custom_field_edit',
                                   meeting_id=meeting.id), data=data)
        assert resp.status_code == 302
        assert meeting.custom_fields.count() == 2
        media_field = CustomField.query.get(2)
        assert participant_field.slug == media_field.slug
        assert participant_field.meeting == media_field.meeting


def test_meeting_custom_field_add_with_same_slug_and_type_fails(app):
    meeting = MeetingFactory()
    role_user = RoleUserMeetingFactory(meeting=meeting,
                                       role__permissions=('manage_meeting',))
    CustomFieldFactory(meeting=meeting)
    data = CustomFieldFactory.attributes()
    data['label-english'] = data['label'].english
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        resp = client.post(url_for('meetings.custom_field_edit',
                                   meeting_id=meeting.id), data=data)
        assert resp.status_code == 200
        assert len(PyQuery(resp.data)('.text-danger small')) == 1
        assert CustomField.query.filter_by(meeting=meeting).count() == 1


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


def test_meeting_custom_fields_list_with_media_participant_enabled(app):
    role_user = RoleUserFactory()
    StaffFactory(user=role_user.user)
    meeting_type = MeetingTypeFactory()
    data = MeetingFactory.attributes()
    data = normalize_data(data)
    data['title-english'] = data.pop('title')
    data['venue_city-english'] = data.pop('venue_city')
    data['badge_header-english'] = data.pop('badge_header')
    data['settings'] = 'media_participant_enabled'
    data['photo_field_id'] = '0'
    data['meeting_type_slug'] = meeting_type.slug

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        resp = client.post(url_for('meetings.edit'), data=data)
        assert resp.status_code == 302
        assert Meeting.query.count() == 1

        resp = client.get(url_for('meetings.custom_fields', meeting_id=1))
        html = PyQuery(resp.data)
        tabs = html('div [role=tabpanel]')
        assert len(tabs) == 3
        participant_list = html('div#participant table tbody tr')
        participant_fields = (CustomField.query
                              .filter_by(meeting_id=1,
                                         custom_field_type=CustomField.PARTICIPANT))
        assert len(participant_list) == participant_fields.count()

        media_list = html('div#media table tbody tr')
        media_fields = (CustomField.query
                        .filter_by(meeting_id=1,
                                   custom_field_type=CustomField.MEDIA))
        assert len(media_list) == media_fields.count()
