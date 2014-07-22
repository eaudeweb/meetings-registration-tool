from mrt.models import Meeting
from flask import url_for
from .factories import MeetingFactory

from datetime import date
from pyquery import PyQuery


def test_model_factory(app):
    MeetingFactory()
    count = Meeting.query.count()
    assert count == 1


def test_meeting_list(app):
    MeetingFactory()
    MeetingFactory()

    client = app.test_client()
    with app.test_request_context():
        url = url_for('meetings.home')
        resp = client.get(url)

    table = PyQuery(resp.data)('#meetings')
    tbody = table('tbody')
    row_count = len(tbody('tr'))

    assert row_count == 2


def test_meeting_add(app):
    data = MeetingFactory.attributes()
    data = normalize_data(data)
    data['title-english'] = data.pop('title')
    data['venue_city-english'] = data.pop('venue_city')

    client = app.test_client()
    with app.test_request_context():
        url = url_for('meetings.edit')
        resp = client.post(url, data=data)

    assert resp.status_code == 302
    assert Meeting.query.count() == 1


def test_meeting_edit(app):
    meeting = MeetingFactory()
    data = normalize_data(MeetingFactory.attributes())
    data['title-english'] = 'Sixtieth meeting of the Standing Committee'
    data['venue_city-english'] = 'Rome'

    client = app.test_client()
    with app.test_request_context():
        url = url_for('meetings.edit', meeting_id=meeting.id)
        resp = client.post(url, data=data)

    assert resp.status_code == 302
    assert Meeting.query.filter(
        Meeting.venue_city.has(english='Rome')).count() == 1


def normalize_data(data):

    def convert_data(value):
        if isinstance(value, date):
            return value.strftime('%d.%m.%Y')
        elif isinstance(value, bool):
            return u'y' if value else u''
        return value

    new_data = dict(data)
    for k, v in new_data.items():
        new_data[k] = convert_data(v)

    return new_data
