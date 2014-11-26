from flask import url_for

from mrt.models import Category
from .factories import MediaParticipantFactory, MeetingCategoryFactory


def test_meeting_media_participant_add(app, user):
    cat = MeetingCategoryFactory(category_type=Category.MEDIA)
    data = MediaParticipantFactory.attributes()
    data['category_id'] = cat.id
    with app.test_request_context():
        with app.client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = app.client.post(url_for('meetings.media_participant_edit',
                                       meeting_id=cat.meeting.id), data=data)
        assert resp.status_code == 302
        assert cat.meeting.media_participants.count() == 1


def test_meeting_media_participant_edit(app, user):
    med_part = MediaParticipantFactory(category__category_type=Category.MEDIA)
    data = MediaParticipantFactory.attributes()
    data['category_id'] = med_part.category.id
    data['first_name'] = name = 'James'
    with app.test_request_context():
        with app.client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = app.client.post(url_for('meetings.media_participant_edit',
                                       meeting_id=med_part.meeting.id,
                                       media_participant_id=med_part.id),
                               data=data)
        assert resp.status_code == 302
        assert med_part.first_name == name


def test_meeting_media_participant_delete(app, user):
    med_part = MediaParticipantFactory()

    with app.test_request_context():
        with app.client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = app.client.delete(url_for('meetings.media_participant_edit',
                                         meeting_id=med_part.meeting.id,
                                         media_participant_id=med_part.id))
        assert resp.status_code == 200
        assert med_part.meeting.media_participants.count() == 0
