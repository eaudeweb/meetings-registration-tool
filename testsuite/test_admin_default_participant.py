from StringIO import StringIO

from flask import url_for
from py.path import local
from pyquery import PyQuery

from sqlalchemy import not_
from sqlalchemy_utils import types

from mrt.models import CustomField, CustomFieldValue

from .factories import MeetingCategoryFactory, ParticipantFactory
from .factories import CustomFieldFactory
from .test_meeting_registration import create_user_after_registration
from .utils import populate_participant_form, add_new_meeting


def test_default_participant_detail(app, user, default_meeting):
    meeting = add_new_meeting(app, user)
    category = MeetingCategoryFactory(meeting=meeting)
    CustomFieldFactory(custom_field_type=CustomField.MEDIA,
                       meeting=meeting)

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        data = ParticipantFactory.attributes()
        data['category_id'] = category.id
        populate_participant_form(meeting, data)
        resp = client.post(url_for('meetings.registration',
                           meeting_id=meeting.id), data=data)
        assert resp.status_code == 200
        assert meeting.participants.count() == 1
        participant = meeting.participants.first()
        create_user_after_registration(client, participant, meeting)
        assert default_meeting.participants.count() == 1

        resp = client.get(url_for('meetings.default_participant_detail',
                          participant_id=2, meeting_id=default_meeting.id))
        assert resp.status_code == 200
        # CHECKS default participant displayed details
        details = PyQuery(resp.data)('tr')
        custom_fields = (
            default_meeting.custom_fields
            .filter_by(custom_field_type=CustomField.PARTICIPANT)
            .filter(not_(CustomField.field_type == CustomField.CATEGORY))
            .order_by(CustomField.sort).all())
        for i, custom_field in enumerate(custom_fields):
            detail_label = details[i].find('th').text_content().strip()
            detail_data = details[i].find('td').text_content().strip()
            participant_data = getattr(participant, custom_field.slug)
            assert custom_field.label.english == detail_label
            if isinstance(participant_data, types.choice.Choice):
                assert participant_data.value == detail_data
            elif isinstance(participant_data, types.country.Country):
                assert participant_data.name == detail_data
            elif isinstance(participant_data, bool):
                if participant_data:
                    assert details[i].find('td').find('span') is not None
            elif custom_field.slug == 'category_id':
                assert participant.category.title.english == detail_data
            else:
                assert str(participant_data) == detail_data

        # CHECKS BREADCRUMB AND MEETING NAVBAR DOES NOT EXIST
        html = PyQuery(resp.data)
        assert len(html('.breadcrumb')) == 0
        assert len(html('.meeting-navs')) == 0
        assert len(html('.actions')) == 1


def test_default_participant_edit(app, user, default_meeting):
    meeting = add_new_meeting(app, user)
    category = MeetingCategoryFactory(meeting=meeting)
    CustomFieldFactory(meeting=meeting, field_type='text',
                       label__english='diet')
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        data = ParticipantFactory.attributes()
        data['category_id'] = category.id
        data['diet'] = 'Vegetarian'
        populate_participant_form(meeting, data)
        resp = client.post(url_for('meetings.registration',
                           meeting_id=meeting.id), data=data)
        assert resp.status_code == 200
        assert meeting.participants.count() == 1
        participant = meeting.participants.first()
        create_user_after_registration(client, participant, meeting)
        assert default_meeting.participants.count() == 1
        default_participant = default_meeting.participants.first()

        data['first_name'] = first_name = 'Johnathan'
        data['diet'] = diet = 'Low fat'
        resp = client.post(url_for('meetings.default_participant_edit',
                                   participant_id=default_participant.id,
                                   meeting_id=default_meeting.id), data=data)
        assert resp.status_code == 302
        assert default_participant.first_name == first_name
        assert participant.first_name != first_name
        cfv = (default_participant.custom_field_values
               .filter(CustomFieldValue.custom_field
                       .has(slug='diet')).first())
        assert cfv.value == diet
        cfv = (participant.custom_field_values
               .filter(CustomFieldValue.custom_field
                       .has(slug='diet')).first())
        assert cfv.value != diet


def test_default_participant_edit_photo_field(app, user, default_meeting):
    upload_dir = local(app.config['UPLOADED_CUSTOM_DEST'])
    meeting = add_new_meeting(app, user)
    category = MeetingCategoryFactory(meeting=meeting)
    CustomFieldFactory(meeting=meeting)

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        data = ParticipantFactory.attributes()
        data['category_id'] = category.id
        data['picture'] = (StringIO('Test'), 'test.png')
        populate_participant_form(meeting, data)
        resp = client.post(url_for('meetings.registration',
                           meeting_id=meeting.id), data=data)
        assert resp.status_code == 200
        assert meeting.participants.count() == 1
        participant = meeting.participants.first()
        photo_field_value = participant.custom_field_values.first().value
        assert upload_dir.join(photo_field_value).check() is True

        create_user_after_registration(client, participant, meeting)
        assert default_meeting.participants.count() == 1
        default_participant = default_meeting.participants.first()
        default_photo_field_value = (default_participant.custom_field_values
                                     .first().value)
        assert upload_dir.join(default_photo_field_value).check() is True
        assert photo_field_value != default_photo_field_value
