from flask import url_for

from .factories import ParticipantFactory


def test_meeting_participant_delete(app):
    part = ParticipantFactory()

    client = app.test_client()
    with app.test_request_context():
        resp = client.delete(url_for('meetings.participant_edit',
                                     meeting_id=part.meeting.id,
                                     participant_id=part.id))
        assert resp.status_code == 200
        assert part.meeting.participants.count() == 0
