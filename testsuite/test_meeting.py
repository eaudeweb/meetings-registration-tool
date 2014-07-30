from flask import url_for
from pyquery import PyQuery
from py.path import local

from mrt.models import Meeting, Category, Phrase
from .factories import MeetingFactory, CategoryDefaultFactory
from .factories import PhraseDefaultFactory, normalize_data


def test_meeting_list(app):
    MeetingFactory.create_batch(5)

    client = app.test_client()
    with app.test_request_context():
        url = url_for('meetings.home')
        resp = client.get(url)

    table = PyQuery(resp.data)('#meetings')
    tbody = table('tbody')
    row_count = len(tbody('tr'))

    assert row_count == 5


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


def test_meeting_delete(app):
    meeting = MeetingFactory()

    client = app.test_client()
    with app.test_request_context():
        url = url_for('meetings.edit', meeting_id=meeting.id)
        resp = client.delete(url)

    assert resp.status_code == 200
    assert Meeting.query.count() == 0


def test_meeting_category_add_list(app):
    CategoryDefaultFactory.create_batch(5)
    meeting = MeetingFactory()

    client = app.test_client()
    with app.test_request_context():
        url = url_for('meetings.categories', meeting_id=meeting.id)
        resp = client.get(url)

        assert resp.status_code == 200
        categories = PyQuery(resp.data)('option')
        assert len(categories) == 5


def test_meeting_category_add_successfully(app):
    category = CategoryDefaultFactory()
    category.background = filename = 'image.jpg'
    upload_dir = local(app.config['UPLOADED_BACKGROUNDS_DEST'])
    upload_dir.ensure(filename)
    meeting = MeetingFactory()
    data = {
        'categories': category.id,
    }

    client = app.test_client()
    with app.test_request_context():
        url = url_for('meetings.categories', meeting_id=meeting.id)
        resp = client.post(url, data=data)

        assert resp.status_code == 302
        assert Category.query.filter_by(meeting_id=meeting.id).count() == 1
        category = Category.query.filter_by(meeting_id=meeting.id).first()
        assert upload_dir.join(category.background).check()


def test_meeting_category_edit_name(app):
    category = CategoryDefaultFactory()
    category.background = filename = 'image.jpg'
    upload_dir = local(app.config['UPLOADED_BACKGROUNDS_DEST'])
    upload_dir.ensure(filename)
    meeting = MeetingFactory()
    data = {
        'categories': category.id,
    }

    client = app.test_client()
    with app.test_request_context():
        url = url_for('meetings.categories', meeting_id=meeting.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 302

        url = url_for('meetings.categories', meeting_id=meeting.id)
        resp = client.get(url)
        assert resp.status_code == 200
        categories = PyQuery(resp.data)('option')
        assert len(categories) == 0
        assert Category.query.filter_by(meeting_id=meeting.id).count() == 1
        category = Category.query.filter_by(meeting_id=meeting.id).first()

        url = url_for('meetings.category_edit', meeting_id=meeting.id,
                      category_id=category.id)
        data = normalize_data(CategoryDefaultFactory.attributes())
        data['title-english'] = 'Media'
        resp = client.post(url, data=data, follow_redirects=True)

        assert resp.status_code == 200
        categories = PyQuery(resp.data)('option')
        assert len(categories) == 1


def test_meeting_category_delete(app):
    category = CategoryDefaultFactory()
    meeting = MeetingFactory()
    data = {
        'categories': category.id,
    }

    client = app.test_client()
    with app.test_request_context():
        url = url_for('meetings.categories', meeting_id=meeting.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 302
        assert Category.query.filter_by(meeting_id=meeting.id).count() == 1
        category = Category.query.filter_by(meeting_id=meeting.id).first()

        url = url_for('meetings.category_edit', meeting_id=meeting.id,
                      category_id=category.id)
        resp = client.delete(url)
        assert resp.status_code == 200
        assert Category.query.filter_by(meeting_id=meeting.id).count() == 0


def test_meeting_add_phrase_edit(app):
    default_phrase = PhraseDefaultFactory()
    data = MeetingFactory.attributes()
    data = normalize_data(data)
    data['title-english'] = data.pop('title')
    data['venue_city-english'] = data.pop('venue_city')
    data['description-english'] = 'Credentials'

    client = app.test_client()
    with app.test_request_context():
        url = url_for('meetings.edit')
        resp = client.post(url, data=data)

        assert resp.status_code == 302
        assert Meeting.query.count() == 1
        meeting = Meeting.query.get(1)
        assert Phrase.query.filter_by(meeting_id=meeting.id).count() == 1
        phrase = Phrase.query.get(1)

        url = url_for('meetings.phrase_edit',
                      meeting_id=meeting.id,
                      meeting_type=meeting.meeting_type,
                      phrase_id=phrase.id)
        resp = client.post(url, data=data)

        assert resp.status_code == 200
        assert default_phrase.description.english != phrase.description.english
