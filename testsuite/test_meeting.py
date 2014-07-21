from mrt.models import Meeting
from flask import url_for
from .factories import MeetingFactory


def test_model_factory(app):
    MeetingFactory()
    count = Meeting.query.count()
    assert count == 1


def test_add_meeting(app):
    data = MeetingFactory.attributes()
    data['online_registration'] = u'y'
    data['date_start'] = data['date_start'].strftime('%d.%m.%Y')
    data['date_end'] = data['date_end'].strftime('%d.%m.%Y')
    data['title-english'] = data.pop('title')
    data['venue_city-english'] = data.pop('venue_city')

    client = app.test_client()
    with app.test_request_context():
        url = url_for('meetings.edit')
        resp = client.post(url, data=data)

    assert resp.status_code == 302
    assert Meeting.query.count() == 1
