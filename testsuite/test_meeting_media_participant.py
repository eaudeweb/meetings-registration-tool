from flask import url_for

from .factories import MediaParticipantFactory, MeetingCategoryFactory


def test_meeting_media_participant_add(app):
    cat = MeetingCategoryFactory()
    data = MediaParticipantFactory.attributes()
    data['category_id'] = cat.id
    client = app.test_client()
    with app.test_request_context():
        resp = client.post(url_for('meetings.media_participant_edit',
                                   meeting_id=cat.meeting.id), data=data)
        assert resp.status_code == 302
        assert cat.meeting.media_participants.scalar()


def test_meeting_media_participant_edit(app):
    med_part = MediaParticipantFactory()
    data = MediaParticipantFactory.attributes()
    data['category_id'] = med_part.category.id
    data['first_name'] = name = 'James'
    client = app.test_client()
    with app.test_request_context():
        resp = client.post(url_for('meetings.media_participant_edit',
                                   meeting_id=med_part.meeting.id,
                                   media_participant_id=med_part.id),
                           data=data)
        assert resp.status_code == 302
        assert med_part.first_name == name


def test_meeting_media_participant_delete(app):
    med_part = MediaParticipantFactory()

    client = app.test_client()
    with app.test_request_context():
        resp = client.delete(url_for('meetings.media_participant_edit',
                                     meeting_id=med_part.meeting.id,
                                     media_participant_id=med_part.id))
        assert resp.status_code == 200
        assert med_part.meeting.media_participants.count() == 0
