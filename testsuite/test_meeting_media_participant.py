from flask import url_for
from pyquery import PyQuery

from mrt.models import Category, Participant
from mrt.forms.meetings import (add_custom_fields_for_meeting,
                                MediaParticipantDummyForm)
from .factories import MediaParticipantFactory, MeetingCategoryFactory
from .factories import MeetingFactory


MEDIA_ENABLED = {'media_participant_enabled': True}


def test_meeting_media_participant_list(app, user):
    category = MeetingCategoryFactory(meeting__settings=MEDIA_ENABLED)
    pass


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
