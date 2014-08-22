from flask import url_for

from .factories import ParticipantFactory, RoleUserFactory, StaffFactory


def test_meeting_participant_delete(app):
    role_user = RoleUserFactory()
    StaffFactory(user=role_user.user)
    part = ParticipantFactory()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        resp = client.delete(url_for('meetings.participant_edit',
                                     meeting_id=part.meeting.id,
                                     participant_id=part.id))
        assert resp.status_code == 200
        assert part.meeting.participants.filter_by(deleted=False).count() == 0
