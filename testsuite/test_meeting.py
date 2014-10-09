from flask import url_for
from pyquery import PyQuery
from py.path import local

from mrt.models import Meeting, Category, Phrase
from .factories import MeetingFactory, CategoryDefaultFactory
from .factories import PhraseDefaultFactory, normalize_data
from .factories import PhraseMeetingFactory, RoleUserFactory, StaffFactory
from .factories import RoleUserMeetingFactory, CustomFieldFactory


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
    role_user = RoleUserFactory()
    StaffFactory(user=role_user.user)
    data = MeetingFactory.attributes()
    data = normalize_data(data)
    data['title-english'] = data.pop('title')
    data['venue_city-english'] = data.pop('venue_city')
    data['badge_header-english'] = data.pop('badge_header')
    data['photo_field_id'] = '0'

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        url = url_for('meetings.edit')
        resp = client.post(url, data=data)

    assert resp.status_code == 302
    assert Meeting.query.count() == 1


def test_meeting_edit(app):
    role_user = RoleUserFactory()
    StaffFactory(user=role_user.user)
    meeting = MeetingFactory()
    data = normalize_data(MeetingFactory.attributes())
    data['title-english'] = 'Sixtieth meeting of the Standing Committee'
    data['venue_city-english'] = 'Rome'
    data['badge_header-english'] = data.pop('badge_header')
    data['photo_field_id'] = '0'

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        url = url_for('meetings.edit', meeting_id=meeting.id)
        resp = client.post(url, data=data)

    assert resp.status_code == 302
    assert Meeting.query.filter(
        Meeting.venue_city.has(english='Rome')).count() == 1
    assert meeting.photo_field is None


def test_meeting_edit_with_photo_field(app):
    role_user = RoleUserFactory()
    StaffFactory(user=role_user.user)
    meeting = MeetingFactory()
    photo_field = CustomFieldFactory(meeting=meeting)
    data = normalize_data(MeetingFactory.attributes())
    data['title-english'] = 'Sixtieth meeting of the Standing Committee'
    data['badge_header-english'] = data.pop('badge_header')
    data['venue_city-english'] = data.pop('venue_city')
    data['photo_field_id'] = photo_field.id

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        url = url_for('meetings.edit', meeting_id=meeting.id)
        resp = client.post(url, data=data)

    assert resp.status_code == 302
    assert meeting.photo_field == photo_field


def test_meeting_delete(app):
    role_user = RoleUserFactory()
    meeting = MeetingFactory()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        url = url_for('meetings.edit', meeting_id=meeting.id)
        resp = client.delete(url)

    assert resp.status_code == 200
    assert Meeting.query.count() == 0


def test_meeting_category_add_list(app):
    CategoryDefaultFactory.create_batch(5)
    meeting = MeetingFactory()
    role_user = RoleUserMeetingFactory(meeting=meeting,
                                       role__permissions=('manage_meeting',))

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
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
    role_user = RoleUserMeetingFactory(meeting=meeting,
                                       role__permissions=('manage_meeting',))
    data = {'categories': category.id}

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        url = url_for('meetings.categories', meeting_id=meeting.id)
        resp = client.post(url, data=data)

        assert resp.status_code == 302
        assert Category.query.filter_by(meeting_id=meeting.id).scalar()
        category = Category.query.filter_by(meeting_id=meeting.id).first()
        assert upload_dir.join(category.background).check()


def test_meeting_category_edit_name(app):
    category = CategoryDefaultFactory()
    category.background = filename = 'image.jpg'
    upload_dir = local(app.config['UPLOADED_BACKGROUNDS_DEST'])
    upload_dir.ensure(filename)
    meeting = MeetingFactory()
    role_user = RoleUserMeetingFactory(meeting=meeting,
                                       role__permissions=('manage_meeting',))
    data = {'categories': category.id}

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        url = url_for('meetings.categories', meeting_id=meeting.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 302

        resp = client.get(url)
        assert resp.status_code == 200
        categories = PyQuery(resp.data)('option')
        assert len(categories) == 0
        assert Category.query.filter_by(meeting_id=meeting.id).scalar()
        category = Category.query.filter_by(meeting_id=meeting.id).first()

        url = url_for('meetings.category_edit', meeting_id=meeting.id,
                      category_id=category.id)
        data = normalize_data(CategoryDefaultFactory.attributes())
        data['title-english'] = title = 'Media'
        resp = client.post(url, data=data, follow_redirects=True)

        assert resp.status_code == 200
        categories = PyQuery(resp.data)('option')
        assert len(categories) == 1
        assert category.title.english == title


def test_meeting_category_delete(app):
    category = CategoryDefaultFactory()
    meeting = MeetingFactory()
    role_user = RoleUserMeetingFactory(meeting=meeting,
                                       role__permissions=('manage_meeting',))
    data = {'categories': category.id}

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        url = url_for('meetings.categories', meeting_id=meeting.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 302
        assert Category.query.filter_by(meeting_id=meeting.id).scalar()
        category = Category.query.filter_by(meeting_id=meeting.id).first()

        url = url_for('meetings.category_edit', meeting_id=meeting.id,
                      category_id=category.id)
        resp = client.delete(url)
        assert resp.status_code == 200
        assert Category.query.filter_by(meeting_id=meeting.id).count() == 0


def test_meeting_phrase_edit_successfully(app):
    phrase = PhraseMeetingFactory()
    role_user = RoleUserMeetingFactory(meeting=phrase.meeting,
                                       role__permissions=('manage_meeting',))
    data = {'description-english': 'Credentials'}

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        url = url_for('meetings.phrase_edit',
                      meeting_id=phrase.meeting.id,
                      meeting_type=phrase.meeting.meeting_type,
                      phrase_id=phrase.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 200
        assert phrase.description.english == 'Credentials'


def test_meeting_add_phrase_edit(app):
    role_user = RoleUserFactory()
    StaffFactory(user=role_user.user)
    default_phrase = PhraseDefaultFactory()
    data = normalize_data(MeetingFactory.attributes())
    data['title-english'] = data.pop('title')
    data['venue_city-english'] = data.pop('venue_city')
    data['badge_header-english'] = data.pop('badge_header')
    data['photo_field_id'] = '0'

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        resp = client.post(url_for('meetings.edit'), data=data)
        assert resp.status_code == 302
        assert Meeting.query.count() == 1
        assert Phrase.query.filter_by(meeting_id=1).scalar()
        phrase = Phrase.query.get(1)

        data = {'description-english': 'Credentials'}
        url = url_for('meetings.phrase_edit',
                      meeting_id=1, meeting_type='cop', phrase_id=phrase.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 200
        assert phrase.description.english == 'Credentials'
        assert default_phrase.description.english != phrase.description.english


def test_meeting_add_default_phrase_edit(app):
    role_user = RoleUserFactory()
    StaffFactory(user=role_user.user)
    default_phrase = PhraseDefaultFactory()
    data = normalize_data(MeetingFactory.attributes())
    data['title-english'] = data.pop('title')
    data['venue_city-english'] = data.pop('venue_city')
    data['badge_header-english'] = data.pop('badge_header')
    data['photo_field_id'] = '0'

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        resp = client.post(url_for('meetings.edit'), data=data)
        assert resp.status_code == 302
        assert Meeting.query.count() == 1
        assert Phrase.query.filter_by(meeting_id=1).scalar()
        phrase = Phrase.query.get(1)

        data = {'description-english': 'Footer'}
        url = url_for('admin.phrase_edit',
                      meeting_type=default_phrase.meeting_type,
                      phrase_id=default_phrase.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 200
        assert default_phrase.description.english == 'Footer'
        assert default_phrase.description.english != phrase.description.english


def test_meeting_add_default_phrase_copies(app):
    role_user = RoleUserFactory()
    StaffFactory(user=role_user.user)
    PhraseDefaultFactory.create_batch(10)
    data = normalize_data(MeetingFactory.attributes())
    data['title-english'] = data.pop('title')
    data['venue_city-english'] = data.pop('venue_city')
    data['photo_field_id'] = '0'
    data['badge_header-english'] = data.pop('badge_header')

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        resp = client.post(url_for('meetings.edit'), data=data)
        assert resp.status_code == 302
        assert Meeting.query.count() == 1
        assert Phrase.query.filter_by(meeting_id=1).count() == 10


def test_meeting_add_with_meeting_settings(app):
    role_user = RoleUserFactory()
    StaffFactory(user=role_user.user)
    data = MeetingFactory.attributes()
    data = normalize_data(data)
    data['title-english'] = data.pop('title')
    data['venue_city-english'] = data.pop('venue_city')
    data['badge_header-english'] = data.pop('badge_header')
    data['photo_field_id'] = '0'
    data['settings'] = 'media_participant_enabled'

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        url = url_for('meetings.edit')
        resp = client.post(url, data=data)

    assert resp.status_code == 302
    assert Meeting.query.count() == 1
    assert Meeting.query.get(1).media_participant_enabled


def test_meeting_edit_with_meeting_settings(app):
    role_user = RoleUserFactory()
    StaffFactory(user=role_user.user)
    meeting = MeetingFactory()
    data = normalize_data(MeetingFactory.attributes())
    data['title-english'] = 'Sixtieth meeting of the Standing Committee'
    data['venue_city-english'] = 'Rome'
    data['photo_field_id'] = '0'
    data['badge_header-english'] = data.pop('badge_header')
    data['settings'] = 'media_participant_enabled'

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id
        url = url_for('meetings.edit', meeting_id=meeting.id)
        resp = client.post(url, data=data)

        assert resp.status_code == 302
        assert Meeting.query.filter(
            Meeting.venue_city.has(english='Rome')).count() == 1
        assert Meeting.query.get(1).media_participant_enabled

        data.pop('settings')
        url = url_for('meetings.edit', meeting_id=meeting.id)
        resp = client.post(url, data=data)

        assert resp.status_code == 302
        assert not Meeting.query.get(1).media_participant_enabled
