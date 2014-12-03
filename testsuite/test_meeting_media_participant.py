from flask import url_for
from pyquery import PyQuery
from urllib import urlencode
from sqlalchemy import not_
from sqlalchemy_utils import types
import json

from mrt.models import Category, Participant, CustomField
from mrt.forms.meetings import (add_custom_fields_for_meeting,
                                MediaParticipantDummyForm)
from .factories import MediaParticipantFactory, MeetingCategoryFactory
from .factories import MeetingFactory, ParticipantFactory, CustomFieldFactory


MEDIA_ENABLED = {'media_participant_enabled': True}


def test_meeting_media_participant_list(app, user):
    category = MeetingCategoryFactory(meeting__settings=MEDIA_ENABLED,
                                      category_type=Category.MEDIA)
    MediaParticipantFactory.create_batch(7, category=category)
    ParticipantFactory.create_batch(5, meeting=category.meeting)
    with app.test_request_context():
        add_custom_fields_for_meeting(category.meeting,
                                      form_class=MediaParticipantDummyForm)
        with app.client.session_transaction() as sess:
            sess['user_id'] = user.id
        data = {
            'columns[0][data]': 'id',
            'columns[1][data]': 'last_name',
            'columns[2][data]': 'category_id',
            'order[0][column]': 0,
            'order[0][dir]': 'asc'
        }
        url = url_for('meetings.media_participants_filter',
                      meeting_id=category.meeting.id)
        url = url + '?' + urlencode(data)
        resp = app.client.get(url)
        assert resp.status_code == 200
        resp_data = json.loads(resp.data)
        assert resp_data['recordsTotal'] == 7
        for participant in resp_data['data']:
            assert (Participant.query.get(participant['id']).participant_type
                    == Participant.MEDIA)


def test_meeting_media_participant_detail_list(app, user):
    category = MeetingCategoryFactory(meeting__settings=MEDIA_ENABLED,
                                      category_type=Category.MEDIA)
    meeting = category.meeting
    data = MediaParticipantFactory.attributes()
    data['category_id'] = category.id

    client = app.test_client()
    with app.test_request_context():
        add_custom_fields_for_meeting(meeting)
        add_custom_fields_for_meeting(meeting,
                                      form_class=MediaParticipantDummyForm)
        CustomFieldFactory(meeting=meeting, field_type='checkbox',
                           label__english='diet')
        CustomFieldFactory(custom_field_type=CustomField.MEDIA,
                           meeting=meeting, field_type='checkbox', sort=30,
                           required=False)
        CustomFieldFactory(meeting=meeting)
        CustomFieldFactory(meeting=meeting, label__english='photo')
        CustomFieldFactory(custom_field_type=CustomField.MEDIA,
                           meeting=meeting, label__english='photo',
                           required=False, sort=31)
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('meetings.media_participant_edit',
                                   meeting_id=meeting.id), data=data)
        assert resp.status_code == 302
        assert Participant.query.current_meeting().media_participants().first()
        participant = Participant.query.get(1)
        resp = client.get(url_for('meetings.media_participant_detail',
                                  meeting_id=meeting.id,
                                  participant_id=1))

        assert resp.status_code == 200
        details = PyQuery(resp.data)('tr')
        custom_fields = (
            meeting.custom_fields
            .filter_by(custom_field_type=CustomField.MEDIA)
            .filter(not_(CustomField.field_type == 'image'))
            .order_by(CustomField.sort).all())
        for i, custom_field in enumerate(custom_fields):
            detail_label = details[i].find('th').text_content().strip()
            detail_data = details[i].find('td').text_content().strip()
            try:
                participant_data = getattr(participant, custom_field.slug)
            except AttributeError:
                value = int(custom_field.custom_field_values.first().value)
                participant_data = True if value else False
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

        image_custom_fields = (
            meeting.custom_fields
            .filter_by(custom_field_type=CustomField.MEDIA,
                       field_type='image')
            .order_by(CustomField.sort).all())
        image_details = PyQuery(resp.data)('.image-widget h4.text-center')
        for i, custom_field in enumerate(image_custom_fields):
            image_label = image_details[i].text_content().strip()
            assert custom_field.label.english == image_label


def test_meeting_media_participant_add(app, user):
    cat = MeetingCategoryFactory(category_type=Category.MEDIA,
                                 meeting__settings=MEDIA_ENABLED)
    data = MediaParticipantFactory.attributes()
    data['category_id'] = cat.id
    with app.test_request_context():
        add_custom_fields_for_meeting(cat.meeting,
                                      form_class=MediaParticipantDummyForm)
        with app.client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = app.client.post(url_for('meetings.media_participant_edit',
                                       meeting_id=cat.meeting.id), data=data)
        assert resp.status_code == 302
        media_participants = (Participant.query
                              .filter_by(meeting=cat.meeting,
                                         participant_type=Participant.MEDIA))
        assert media_participants.count() == 1


def test_meeting_media_participant_edit(app, user):
    med_part = MediaParticipantFactory(category__meeting__settings=MEDIA_ENABLED,
                                       category__category_type=Category.MEDIA)
    data = MediaParticipantFactory.attributes()
    data['category_id'] = med_part.category.id
    data['first_name'] = name = 'James'
    with app.test_request_context():
        add_custom_fields_for_meeting(med_part.meeting,
                                      form_class=MediaParticipantDummyForm)
        with app.client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = app.client.post(url_for('meetings.media_participant_edit',
                                       meeting_id=med_part.meeting.id,
                                       participant_id=med_part.id),
                               data=data)
        assert resp.status_code == 302
        assert med_part.first_name == name


def test_meeting_media_participant_delete(app, user):
    med_part = MediaParticipantFactory(category__meeting__settings=MEDIA_ENABLED,
                                       category__category_type=Category.MEDIA)

    with app.test_request_context():
        add_custom_fields_for_meeting(med_part.meeting,
                                      form_class=MediaParticipantDummyForm)
        with app.client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = app.client.delete(url_for('meetings.media_participant_edit',
                                         meeting_id=med_part.meeting.id,
                                         participant_id=med_part.id))
        assert resp.status_code == 200
        media_participants = (Participant.query
                              .filter_by(meeting=med_part.meeting,
                                         participant_type=Participant.MEDIA)
                              .active())
        assert media_participants.count() == 0


def test_meeting_media_partcipant_add_categories(app, user):
    meeting = MeetingFactory(settings='media_participant_enabled')
    MeetingCategoryFactory.create_batch(3, meeting=meeting,
                                        category_type=Category.MEDIA)
    MeetingCategoryFactory.create_batch(2, meeting=meeting)

    with app.test_request_context():
        add_custom_fields_for_meeting(meeting,
                                      form_class=MediaParticipantDummyForm)
        with app.client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = app.client.get(url_for('meetings.media_participant_edit',
                                      meeting_id=meeting.id))
        categories = PyQuery(resp.data)('input[name=category_id]')
        assert len(categories) == 3
        for category in categories:
            cat_id = category.attrib['value']
            assert (Category.query.get(int(cat_id)).category_type ==
                    Category.MEDIA)
