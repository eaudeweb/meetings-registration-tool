from flask import url_for

from mrt.models import Meeting

from testsuite.factories import MeetingFactory, normalize_data


def test_default_participant_detail(app, user, default_meeting):

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        meeting = add_new_meeting(client)
        #TODO


def add_new_meeting(client):
    data = normalize_data(MeetingFactory.attributes())
    data['title-english'] = data.pop('title')
    data['acronym'] = acronym = 'TEST'
    data['venue_city-english'] = data.pop('venue_city')
    data['badge_header-english'] = data.pop('badge_header')
    data['online_registration'] = 'y'
    data['photo_field_id'] = '0'

    url = url_for('meetings.edit')
    resp = client.post(url, data=data)

    assert resp.status_code == 302
    return Meeting.query.filter_by(acronym=acronym).first()
