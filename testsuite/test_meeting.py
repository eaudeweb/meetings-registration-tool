from flask import url_for
from pyquery import PyQuery
from py.path import local
import json

from mrt.models import Meeting, Category, Phrase, CustomField, Condition
from mrt.models import CustomFieldChoice, Translation, Participant, Action
from mrt.forms.meetings import ParticipantDummyForm, MediaParticipantDummyForm
from mrt.forms.meetings import add_custom_fields_for_meeting

from .factories import CategoryDefaultFactory, StaffFactory
from .factories import PhraseDefaultFactory, RoleUserMeetingFactory
from .factories import PhraseMeetingFactory, ParticipantFactory
from .factories import CustomFieldFactory, MeetingCategoryFactory
from .factories import MeetingFactory, MeetingTypeFactory, normalize_data
from .factories import UserNotificationFactory, MediaParticipantFactory
from .factories import ActionFactory, ConditionValueFactory


def test_meeting_list(app, user, default_meeting):
    MeetingFactory.create_batch(5)

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('meetings.home')
        resp = client.get(url)

    table = PyQuery(resp.data)('#meetings')
    tbody = table('tbody')
    row_count = len(tbody('tr'))
    assert row_count == 5


def test_meeting_list_for_role_user(app, default_meeting):
    staff = StaffFactory()
    MeetingFactory.create_batch(3)
    MeetingFactory(owner=staff)
    RoleUserMeetingFactory.create_batch(3, user=staff.user, staff=staff)

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = staff.user.id
        url = url_for('meetings.home')
        resp = client.get(url)

    table = PyQuery(resp.data)('#meetings')
    tbody = table('tbody')
    row_count = len(tbody('tr'))
    assert row_count == 4


def test_meeting_list_filter(app, user, default_meeting):
    MeetingFactory.create_batch(3)
    meeting_type = MeetingTypeFactory(slug='sc')
    MeetingFactory.create_batch(6, meeting_type=meeting_type)

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.get(url_for('meetings.home'))

        assert resp.status_code == 200
        table = PyQuery(resp.data)('#meetings')
        tbody = table('tbody')
        row_count = len(tbody('tr'))
        assert row_count == 9

        resp = client.get(url_for('meetings.home', meeting_type='sc'))
        assert resp.status_code == 200
        table = PyQuery(resp.data)('#meetings')
        tbody = table('tbody')
        row_count = len(tbody('tr'))
        assert row_count == 6


def test_meeting_add(app, user):
    data = normalize_data(MeetingFactory.attributes())
    meeting_type = MeetingTypeFactory()
    data['title-english'] = data.pop('title')
    data['venue_city-english'] = data.pop('venue_city')
    data['badge_header-english'] = data.pop('badge_header')
    data['photo_field_id'] = data['media_photo_field_id'] = '0'
    data['meeting_type_slug'] = meeting_type.slug

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('meetings.add')
        resp = client.post(url, data=data)

    assert resp.status_code == 302
    assert Meeting.query.count() == 1


def test_meeting_add_default_categories_clone(app, user):
    data = normalize_data(MeetingFactory.attributes())
    categories = CategoryDefaultFactory.create_batch(3)
    meeting_type = MeetingTypeFactory(default_categories=categories)
    data['title-english'] = data.pop('title')
    data['venue_city-english'] = data.pop('venue_city')
    data['badge_header-english'] = data.pop('badge_header')
    data['photo_field_id'] = data['media_photo_field_id'] = '0'
    data['meeting_type_slug'] = meeting_type.slug

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('meetings.add')
        resp = client.post(url, data=data)

    assert resp.status_code == 302
    assert Meeting.query.count() == 1
    meeting = Meeting.query.first()
    assert meeting.categories.count() == 3


def test_meeting_add_no_meeting_type(app, user):
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('meetings.add')
        resp = client.get(url)

    assert resp.status_code == 200
    meeting_type_required_warning = PyQuery(resp.data)('h3.text-danger')
    assert len(meeting_type_required_warning) == 1


def test_meeting_add_without_badge_header(app, user):
    data = normalize_data(MeetingFactory.attributes())
    meeting_type = MeetingTypeFactory()
    data['title-english'] = data.pop('title')
    data['venue_city-english'] = data.pop('venue_city')
    data['photo_field_id'] = data['media_photo_field_id'] = '0'
    data['meeting_type_slug'] = meeting_type.slug

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('meetings.add')
        resp = client.post(url, data=data)

    assert resp.status_code == 302
    assert Meeting.query.count() == 1
    meeting = Meeting.query.get(1)
    assert meeting.badge_header is None


def test_meeting_add_participant_custom_field_generation(app, user):
    data = normalize_data(MeetingFactory.attributes())
    meeting_type = MeetingTypeFactory()
    data['title-english'] = data.pop('title')
    data['venue_city-english'] = data.pop('venue_city')
    data['badge_header-english'] = data.pop('badge_header')
    data['photo_field_id'] = data['media_photo_field_id'] = '0'
    data['meeting_type_slug'] = meeting_type.slug

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('meetings.add'), data=data)
        assert resp.status_code == 302
        assert Meeting.query.count() == 1

        fields = ParticipantDummyForm()._fields
        query = CustomField.query.filter_by(meeting_id=1)
        assert query.count() == len(fields)

        for field in fields.values():
            (CustomField.query
             .filter_by(meeting_id=1, slug=field.name,
                        custom_field_type=CustomField.PARTICIPANT)
             .filter(CustomField.label.has(english=field.label.text))
             .one())


def test_meeting_add_with_media_participants_disabled(app, user):
    data = normalize_data(MeetingFactory.attributes())
    meeting_type = MeetingTypeFactory()
    data['title-english'] = data.pop('title')
    data['venue_city-english'] = data.pop('venue_city')
    data['badge_header-english'] = data.pop('badge_header')
    data['photo_field_id'] = data['media_photo_field_id'] = '0'
    data['settings'] = 'media_participant_enabled'
    data['meeting_type_slug'] = meeting_type.slug

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('meetings.add'), data=data)
        assert resp.status_code == 302
        assert Meeting.query.count() == 1

        participant_fields = ParticipantDummyForm()._fields
        media_fields = MediaParticipantDummyForm()._fields
        query = CustomField.query.filter_by(meeting_id=1)
        assert query.count() == len(participant_fields) + len(media_fields)

        for field in media_fields.values():
            (CustomField.query
             .filter_by(meeting_id=1, slug=field.name,
                        custom_field_type=CustomField.MEDIA)
             .filter(CustomField.label.has(english=field.label.text))
             .one())


def test_meeting_add_custom_field_choice_generation(app, user):
    data = normalize_data(MeetingFactory.attributes())
    meeting_type = MeetingTypeFactory()
    data['title-english'] = data.pop('title')
    data['venue_city-english'] = data.pop('venue_city')
    data['badge_header-english'] = data.pop('badge_header')
    data['photo_field_id'] = data['media_photo_field_id'] = '0'
    data['meeting_type_slug'] = meeting_type.slug

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('meetings.add'), data=data)
        assert resp.status_code == 302
        assert Meeting.query.count() == 1

        query = CustomField.query.filter_by(
            meeting_id=1, field_type=CustomField.SELECT)
        fields = [f for f in ParticipantDummyForm()._fields.values()
                  if f.type == 'SelectField']
        assert query.count() == len(fields)
        for field in fields:
            query = (
                CustomFieldChoice.query
                .filter(CustomFieldChoice.custom_field.has(slug=field.name)))
            assert query.count() == len(field.choices)


def test_meeting_primary_custom_fields_noneditable_and_nondeletable(app, user):
    data = normalize_data(MeetingFactory.attributes())
    meeting_type = MeetingTypeFactory()
    data['title-english'] = data.pop('title')
    data['venue_city-english'] = data.pop('venue_city')
    data['badge_header-english'] = data.pop('badge_header')
    data['photo_field_id'] = data['media_photo_field_id'] = '0'
    data['settings'] = 'media_participant_enabled'
    data['meeting_type_slug'] = meeting_type.slug

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('meetings.add')
        resp = client.post(url, data=data)

        assert resp.status_code == 302
        assert Meeting.query.count() == 1
        field_query = CustomField.query.filter_by(meeting_id=1)

        for field in field_query:
            data = CustomFieldFactory.attributes()
            url = url_for('meetings.custom_field_edit',
                          meeting_id=field.meeting.id,
                          custom_field_id=field.id)
            resp = client.post(url, data=data)
            assert resp.status_code == 404
            resp = client.delete(url)
            assert resp.status_code == 404


def test_meeting_edit(app, user):
    meeting = MeetingFactory()
    data = normalize_data(MeetingFactory.attributes())
    data['title-english'] = 'Sixtieth meeting of the Standing Committee'
    data['venue_city-english'] = 'Rome'
    data['badge_header-english'] = data.pop('badge_header')
    data['photo_field_id'] = data['media_photo_field_id'] = '0'

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('meetings.edit', meeting_id=meeting.id)
        resp = client.post(url, data=data)

    assert resp.status_code == 302
    assert Meeting.query.filter(
        Meeting.venue_city.has(english='Rome')).count() == 1
    assert meeting.photo_field is None


def test_meeting_edit_with_photo_field(app, user):
    meeting = MeetingFactory()
    photo_field = CustomFieldFactory(meeting=meeting)
    data = normalize_data(MeetingFactory.attributes())
    data['title-english'] = 'Sixtieth meeting of the Standing Committee'
    data['badge_header-english'] = data.pop('badge_header')
    data['venue_city-english'] = data.pop('venue_city')
    data['photo_field_id'] = photo_field.id
    data['media_photo_field_id'] = '0'

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('meetings.edit', meeting_id=meeting.id)
        resp = client.post(url, data=data)

    assert resp.status_code == 302
    assert meeting.photo_field == photo_field


def test_meeting_edit_with_media_photo_field(app, user):
    MEDIA_ENABLED = {'media_participant_enabled': True}
    meeting = MeetingFactory(settings=MEDIA_ENABLED)
    photo_field = CustomFieldFactory(meeting=meeting,
                                     custom_field_type=CustomField.MEDIA)
    data = normalize_data(MeetingFactory.attributes())
    data['title-english'] = 'Sixtieth meeting of the Standing Committee'
    data['badge_header-english'] = data.pop('badge_header')
    data['venue_city-english'] = data.pop('venue_city')
    data['photo_field_id'] = '0'
    data['media_photo_field_id'] = photo_field.id

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('meetings.edit', meeting_id=meeting.id)
        resp = client.post(url, data=data)

    assert resp.status_code == 302
    assert meeting.media_photo_field == photo_field


def test_meeting_edit_with_photo_field_and_media_field_choice(app, user):
    MEDIA_ENABLED = {'media_participant_enabled': True}
    meeting = MeetingFactory(settings=MEDIA_ENABLED)
    photo_field = CustomFieldFactory(meeting=meeting,
                                     custom_field_type=CustomField.MEDIA)
    data = normalize_data(MeetingFactory.attributes())
    data['title-english'] = 'Sixtieth meeting of the Standing Committee'
    data['badge_header-english'] = data.pop('badge_header')
    data['venue_city-english'] = data.pop('venue_city')
    data['photo_field_id'] = photo_field.id
    data['media_photo_field_id'] = '0'

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('meetings.edit', meeting_id=meeting.id)
        resp = client.post(url, data=data)

    assert resp.status_code == 200
    error = PyQuery(resp.data)('div.text-danger small')
    assert len(error) == 1
    assert error.text() == 'Not a valid choice'


def test_meeting_edit_with_media_photo_field_and_field_choice(app, user):
    MEDIA_ENABLED = {'media_participant_enabled': True}
    meeting = MeetingFactory(settings=MEDIA_ENABLED)
    photo_field = CustomFieldFactory(meeting=meeting)
    data = normalize_data(MeetingFactory.attributes())
    data['title-english'] = 'Sixtieth meeting of the Standing Committee'
    data['badge_header-english'] = data.pop('badge_header')
    data['venue_city-english'] = data.pop('venue_city')
    data['photo_field_id'] = '0'
    data['media_photo_field_id'] = photo_field.id

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('meetings.edit', meeting_id=meeting.id)
        resp = client.post(url, data=data)

    assert resp.status_code == 200
    error = PyQuery(resp.data)('div.text-danger small')
    assert len(error) == 1
    assert error.text() == 'Not a valid choice'


def test_meeting_edit_form_with_media_photo_field(app, user):
    MEDIA_ENABLED = {'media_participant_enabled': True}
    meeting = MeetingFactory(settings=MEDIA_ENABLED)
    CustomFieldFactory(meeting=meeting)
    CustomFieldFactory(meeting=meeting,
                       custom_field_type=CustomField.MEDIA)

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.get(url_for('meetings.edit', meeting_id=meeting.id))

    assert resp.status_code == 200
    html = PyQuery(resp.data)
    photo_field = html('#photo_field_id')
    assert len(photo_field) == 1
    assert len(photo_field[0].value_options) == 2
    media_photo_field = html('#media_photo_field_id')
    assert len(media_photo_field) == 1
    assert len(media_photo_field[0].value_options) == 2


def test_meeting_edit_form_without_media_photo_field(app, user):
    meeting = MeetingFactory()
    CustomFieldFactory(meeting=meeting)
    CustomFieldFactory(meeting=meeting,
                       custom_field_type=CustomField.MEDIA)

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.get(url_for('meetings.edit', meeting_id=meeting.id))

    assert resp.status_code == 200
    html = PyQuery(resp.data)
    photo_field = html('#photo_field_id')
    assert len(photo_field) == 1
    assert len(photo_field[0].value_options) == 2
    media_photo_field = html('#media_photo_field_id')
    assert len(media_photo_field) == 0


def test_meeting_edit_removes_badge_header(app, user):
    meeting = MeetingFactory()
    badge_header = meeting.badge_header.english
    assert Translation.query.filter_by(english=badge_header).count() == 1
    data = normalize_data(MeetingFactory.attributes())
    data['title-english'] = 'Sixtieth meeting of the Standing Committee'
    data['venue_city-english'] = 'Rome'
    data['photo_field_id'] = data['media_photo_field_id'] = '0'

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('meetings.edit', meeting_id=meeting.id)
        resp = client.post(url, data=data)

        assert resp.status_code == 302
        assert meeting.badge_header is None
        assert Translation.query.filter_by(english=badge_header).count() == 0


def test_meeting_delete(app, user):
    meeting = MeetingFactory()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('meetings.edit', meeting_id=meeting.id)
        resp = client.delete(url)

    assert resp.status_code == 200
    assert Meeting.query.count() == 0


def test_meeting_participant_category_required(app, user):
    meeting = MeetingFactory()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.get(url_for('meetings.participant_edit',
                                  meeting_id=meeting.id))
        assert resp.status_code == 200
        category_required = PyQuery(resp.data)('h3.text-danger')
        assert len(category_required) == 1


def test_meeting_media_participant_category_required(app, user):
    meeting = MeetingFactory()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.get(url_for('meetings.media_participant_edit',
                                  meeting_id=meeting.id))
        assert resp.status_code == 200
        category_required = PyQuery(resp.data)('h3.text-danger')
        assert len(category_required) == 1


def test_meeting_category_add_list(app, user):
    CategoryDefaultFactory.create_batch(5)
    meeting = MeetingFactory()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('meetings.categories', meeting_id=meeting.id)
        resp = client.get(url)

        assert resp.status_code == 200
        categories = PyQuery(resp.data)('option')
        assert len(categories) == 5


def test_meeting_category_add_successfully(app, user):
    category = CategoryDefaultFactory()
    category.background = filename = 'image.jpg'
    upload_dir = local(app.config['UPLOADED_BACKGROUNDS_DEST'])
    upload_dir.ensure(filename)
    meeting = MeetingFactory()
    data = {'categories': category.id}

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('meetings.categories', meeting_id=meeting.id)
        resp = client.post(url, data=data)

        assert resp.status_code == 302
        assert Category.query.filter_by(meeting_id=meeting.id).scalar()
        category = Category.query.filter_by(meeting_id=meeting.id).first()
        assert upload_dir.join(category.background).check()


def test_meeting_category_edit_name(app, user):
    category = CategoryDefaultFactory()
    category.background = filename = 'image.jpg'
    upload_dir = local(app.config['UPLOADED_BACKGROUNDS_DEST'])
    upload_dir.ensure(filename)
    meeting = MeetingFactory()
    data = {'categories': category.id}

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
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


def test_meeting_category_edit_with_same_title_fails(app, user):
    category = MeetingCategoryFactory(title__english='Reporter')
    member_category = MeetingCategoryFactory(meeting=category.meeting)

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        data = normalize_data(MeetingCategoryFactory.attributes())
        data['title-english'] = member_category.title.english
        url = url_for('meetings.category_edit', meeting_id=category.meeting.id,
                      category_id=category.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 200
        assert category.title.english != member_category.title.english


def test_meeting_category_delete(app, user):
    category = CategoryDefaultFactory()
    meeting = MeetingFactory()
    data = {'categories': category.id}

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
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


def test_meeting_category_delete_with_participants(app, user):
    participant = ParticipantFactory()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.delete(url_for('meetings.category_edit',
                                     meeting_id=participant.meeting.id,
                                     category_id=participant.category.id))
        assert resp.status_code == 200
        resp_data = json.loads(resp.data)
        assert resp_data['status'] == 'error'
        assert Category.query.filter_by(meeting=participant.meeting).first()


def test_meeting_category_delete_with_media_participants(app, user):
    MEDIA_ENABLED = {'media_participant_enabled': True}
    med_part = ParticipantFactory(category__meeting__settings=MEDIA_ENABLED,
                                  category__category_type=Category.MEDIA,
                                  participant_type=Participant.MEDIA)

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.delete(url_for('meetings.category_edit',
                                     meeting_id=med_part.meeting.id,
                                     category_id=med_part.category.id))
        assert resp.status_code == 200
        resp_data = json.loads(resp.data)
        assert resp_data['status'] == 'error'
        assert Category.query.filter_by(meeting=med_part.meeting).first()


def test_meeting_phrase_edit_successfully(app, user):
    phrase = PhraseMeetingFactory()
    data = {'description-english': 'Credentials'}

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('meetings.phrase_edit',
                      meeting_id=phrase.meeting.id,
                      meeting_type=phrase.meeting.meeting_type,
                      phrase_id=phrase.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 200
        assert phrase.description.english == 'Credentials'


def test_meeting_add_phrase_edit(app, user):
    default_phrase = PhraseDefaultFactory()
    data = normalize_data(MeetingFactory.attributes())
    data['title-english'] = data.pop('title')
    data['venue_city-english'] = data.pop('venue_city')
    data['badge_header-english'] = data.pop('badge_header')
    data['photo_field_id'] = data['media_photo_field_id'] = '0'
    data['meeting_type_slug'] = default_phrase.meeting_type_slug

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('meetings.add'), data=data)
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


def test_meeting_add_default_phrase_edit(app, user):
    default_phrase = PhraseDefaultFactory()
    data = normalize_data(MeetingFactory.attributes())
    data['title-english'] = data.pop('title')
    data['venue_city-english'] = data.pop('venue_city')
    data['badge_header-english'] = data.pop('badge_header')
    data['photo_field_id'] = data['media_photo_field_id'] = '0'
    data['meeting_type_slug'] = default_phrase.meeting_type_slug

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('meetings.add'), data=data)
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


def test_meeting_add_default_phrase_copies(app, user):
    meeting_type = MeetingTypeFactory()
    PhraseDefaultFactory.create_batch(10, meeting_type=meeting_type)
    data = normalize_data(MeetingFactory.attributes())
    data['title-english'] = data.pop('title')
    data['venue_city-english'] = data.pop('venue_city')
    data['photo_field_id'] = data['media_photo_field_id'] = '0'
    data['badge_header-english'] = data.pop('badge_header')
    data['meeting_type_slug'] = meeting_type.slug

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.post(url_for('meetings.add'), data=data)
        assert resp.status_code == 302
        assert Meeting.query.count() == 1
        assert Phrase.query.filter_by(meeting_id=1).count() == 10


def test_meeting_add_with_meeting_settings(app, user):
    data = normalize_data(MeetingFactory.attributes())
    meeting_type = MeetingTypeFactory()
    data['title-english'] = data.pop('title')
    data['venue_city-english'] = data.pop('venue_city')
    data['badge_header-english'] = data.pop('badge_header')
    data['photo_field_id'] = data['media_photo_field_id'] = '0'
    data['settings'] = 'media_participant_enabled'
    data['meeting_type_slug'] = meeting_type.slug

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('meetings.add')
        resp = client.post(url, data=data)

    assert resp.status_code == 302
    assert Meeting.query.count() == 1
    assert Meeting.query.get(1).media_participant_enabled


def test_meeting_edit_with_meeting_settings(app, user):
    meeting = MeetingFactory()
    data = normalize_data(MeetingFactory.attributes())
    data['title-english'] = 'Sixtieth meeting of the Standing Committee'
    data['venue_city-english'] = 'Rome'
    data['photo_field_id'] = data['media_photo_field_id'] = '0'
    data['badge_header-english'] = data.pop('badge_header')
    data['settings'] = 'media_participant_enabled'

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
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


def test_clone_meeting_default_values(app, user):
    meeting = MeetingFactory()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('meetings.clone', meeting_id=meeting.id)
        resp = client.get(url)
        html = PyQuery(resp.data)
        assert html('#title-english').val() == meeting.title.english
        assert html('#title-french').val() == meeting.title.french
        assert html('#title-spanish').val() == meeting.title.spanish
        assert (html('#badge_header-english').val() ==
                meeting.badge_header.english)
        assert (html('#badge_header-french').val() ==
                meeting.badge_header.french)
        assert (html('#badge_header-spanish').val() ==
                meeting.badge_header.spanish)
        assert html('#venue_address').text() == meeting.venue_address
        assert (html('#venue_country option:selected').val() ==
                meeting.venue_country)
        assert html('#venue_city-english').val() == meeting.venue_city.english
        assert html('#venue_city-french').val() == meeting.venue_city.french
        assert html('#venue_city-spanish').val() == meeting.venue_city.spanish
        assert (html('#date_start').val() ==
                meeting.date_start.strftime('%d.%m.%Y'))
        assert html('#date_end').val() == meeting.date_end.strftime('%d.%m.%Y')
        assert (html('#meeting_type_slug option:selected').val() ==
                meeting.meeting_type_slug)
        assert html('#acronym').val() is None
        assert (html('#online_registration').is_(':checked') ==
                meeting.online_registration)
        assert (html('#settings-0').is_(':checked') ==
                bool(meeting.media_participant_enabled))
        assert html('#photo_field_id').val() == meeting.photo_field_id or 0


def test_clone_meeting_same_acronym(app, user):
    meeting = MeetingFactory()
    data = normalize_data(MeetingFactory.attributes())
    data['title-english'] = data.pop('title')
    data['venue_city-english'] = data.pop('venue_city')
    data['badge_header-english'] = data.pop('badge_header')
    data['photo_field_id'] = data['media_photo_field_id'] = '0'
    data['meeting_type_slug'] = meeting.meeting_type.slug
    data['acronym'] = meeting.acronym

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('meetings.clone', meeting_id=meeting.id)
        resp = client.post(url, data=data)
        acronym_error = PyQuery(resp.data)('div.text-danger small')
        assert len(acronym_error) == 1
        assert acronym_error.text() == 'Acronym exists'


def test_clone_meeting_attributes_are_equal(app, user):
    meeting = MeetingFactory()
    data = normalize_data(MeetingFactory.attributes())
    data['title-english'] = data.pop('title')
    data['venue_city-english'] = data.pop('venue_city')
    data['badge_header-english'] = data.pop('badge_header')
    data['photo_field_id'] = data['media_photo_field_id'] = '0'
    data['meeting_type_slug'] = meeting.meeting_type.slug

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('meetings.clone', meeting_id=meeting.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 302
        assert Meeting.query.count() == 2
        clone = Meeting.query.get(2)
        check_translations_are_equal(meeting.title, clone.title)
        check_translations_are_equal(meeting.badge_header,
                                     clone.badge_header)
        check_translations_are_equal(meeting.venue_city,
                                     clone.venue_city)
        assert meeting.venue_address is not clone.venue_address
        assert meeting.venue_address == clone.venue_address
        assert meeting.venue_country is not clone.venue_country
        assert meeting.venue_country == clone.venue_country
        assert meeting.date_start is not clone.date_start
        assert meeting.date_start == clone.date_start
        assert meeting.date_end is not clone.date_end
        assert meeting.date_end == clone.date_end
        assert (meeting.meeting_type_slug is not clone.meeting_type_slug)
        assert (meeting.meeting_type_slug == clone.meeting_type_slug)
        assert meeting.acronym != clone.acronym
        assert meeting.online_registration == clone.online_registration


def test_clone_meeting_custom_fields_clones(app, user):
    MEDIA_ENABLED = {'media_participant_enabled': True}
    meeting = MeetingFactory(settings=MEDIA_ENABLED)
    CustomFieldFactory(meeting=meeting, field_type='checkbox',
                       label__english='diet')
    CustomFieldFactory(custom_field_type=CustomField.MEDIA,
                       meeting=meeting, field_type='checkbox', sort=30,
                       required=False)
    CustomFieldFactory(meeting=meeting)
    CustomFieldFactory(meeting=meeting, field_type='text',
                       label__english='Info',
                       visible_on_registration_form=False)
    data = normalize_data(MeetingFactory.attributes())
    data['title-english'] = data.pop('title')
    data['venue_city-english'] = data.pop('venue_city')
    data['badge_header-english'] = data.pop('badge_header')
    data['photo_field_id'] = data['media_photo_field_id'] = '0'
    data['meeting_type_slug'] = meeting.meeting_type.slug

    client = app.test_client()
    with app.test_request_context():
        add_custom_fields_for_meeting(meeting)
        add_custom_fields_for_meeting(meeting,
                                      form_class=MediaParticipantDummyForm)
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('meetings.clone', meeting_id=meeting.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 302
        assert Meeting.query.count() == 2
        clone = Meeting.query.get(2)
        fields = meeting.custom_fields.order_by(CustomField.sort).all()
        cloned_fields = clone.custom_fields.order_by(CustomField.sort).all()
        assert len(fields) == len(cloned_fields)
        for (field, cloned_field) in zip(fields, cloned_fields):
            check_fields_are_equal(field, cloned_field)


def test_clone_meeting_category_clones(app, user):
    MEDIA_ENABLED = {'media_participant_enabled': True}
    meeting = MeetingFactory(settings=MEDIA_ENABLED)
    MeetingCategoryFactory(meeting=meeting)
    MeetingCategoryFactory(meeting=meeting, category_type=Category.MEDIA)

    data = normalize_data(MeetingFactory.attributes())
    data['title-english'] = data.pop('title')
    data['venue_city-english'] = data.pop('venue_city')
    data['badge_header-english'] = data.pop('badge_header')
    data['photo_field_id'] = data['media_photo_field_id'] = '0'
    data['meeting_type_slug'] = meeting.meeting_type.slug

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('meetings.clone', meeting_id=meeting.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 302
        assert Meeting.query.count() == 2
        clone = Meeting.query.get(2)
        categs = meeting.categories.all()
        cloned_categs = clone.categories.all()
        assert len(categs) == len(cloned_categs)
        for (categ, cloned_categ) in zip(categs, cloned_categs):
            check_categories_are_equal(categ, cloned_categ)


def test_clone_meeting_role_clones(app, user):
    MEDIA_ENABLED = {'media_participant_enabled': True}
    meeting = MeetingFactory(settings=MEDIA_ENABLED)
    RoleUserMeetingFactory.create_batch(5, meeting=meeting)

    data = normalize_data(MeetingFactory.attributes())
    data['title-english'] = data.pop('title')
    data['venue_city-english'] = data.pop('venue_city')
    data['badge_header-english'] = data.pop('badge_header')
    data['photo_field_id'] = data['media_photo_field_id'] = '0'
    data['meeting_type_slug'] = meeting.meeting_type.slug

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('meetings.clone', meeting_id=meeting.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 302
        assert Meeting.query.count() == 2
        clone = Meeting.query.get(2)
        role_users = meeting.role_users.all()
        cloned_role_users = clone.role_users.all()
        for (role, cloned_role) in zip(role_users, cloned_role_users):
            assert role is not cloned_role
            assert role.user is cloned_role.user
            assert role.role is cloned_role.role


def test_clone_meeting_subscriber_clones(app, user):
    MEDIA_ENABLED = {'media_participant_enabled': True}
    meeting = MeetingFactory(settings=MEDIA_ENABLED)
    UserNotificationFactory.create_batch(3, meeting=meeting)
    UserNotificationFactory(meeting=meeting,
                            notification_type='notify_media')

    data = normalize_data(MeetingFactory.attributes())
    data['title-english'] = data.pop('title')
    data['venue_city-english'] = data.pop('venue_city')
    data['badge_header-english'] = data.pop('badge_header')
    data['photo_field_id'] = data['media_photo_field_id'] = '0'
    data['meeting_type_slug'] = meeting.meeting_type.slug

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('meetings.clone', meeting_id=meeting.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 302
        assert Meeting.query.count() == 2
        clone = Meeting.query.get(2)
        subscribers = meeting.user_notifications.all()
        cloned_subscribers = clone.user_notifications.all()
        assert len(subscribers) == len(cloned_subscribers)
        for (sub, cloned_sub) in zip(subscribers, cloned_subscribers):
            assert sub is not cloned_sub
            assert sub.user is cloned_sub.user
            assert sub.notification_type == cloned_sub.notification_type


def test_clone_meeting_rules_clones(app, user):
    category = MeetingCategoryFactory(meeting__online_registration=True)
    meeting = category.meeting
    birth_field = CustomFieldFactory(label__english='Place of birth',
                                     meeting=meeting,
                                     field_type='country')
    passport_field = CustomFieldFactory(label__english='Passport Photo',
                                        meeting=meeting,
                                        required=False)
    info_field = CustomFieldFactory(label__english='Extra info',
                                    meeting=meeting,
                                    field_type='text',
                                    required=False)

    data = normalize_data(MeetingFactory.attributes())
    data['title-english'] = data.pop('title')
    data['venue_city-english'] = data.pop('venue_city')
    data['badge_header-english'] = data.pop('badge_header')
    data['photo_field_id'] = data['media_photo_field_id'] = '0'
    data['meeting_type_slug'] = meeting.meeting_type.slug

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        add_custom_fields_for_meeting(meeting)
        fields = meeting.custom_fields
        country_field = fields.filter_by(slug='country').one()
        category_field = fields.filter_by(slug='category_id').one()
        country_cond = ConditionValueFactory(condition__rule__meeting=meeting,
                                             condition__field=country_field,
                                             value='RO')
        ConditionValueFactory(condition__rule=country_cond.condition.rule,
                              condition__field=category_field,
                              value=category.id)
        ConditionValueFactory(condition__rule=country_cond.condition.rule,
                              condition__field=birth_field,
                              value='AZ')
        ActionFactory(rule=country_cond.condition.rule,
                      field=passport_field,
                      is_required=True)
        ActionFactory(rule=country_cond.condition.rule,
                      field=info_field,
                      is_required=True)

        resp = client.post(url_for('meetings.clone', meeting_id=meeting.id),
                           data=data)
        assert resp.status_code == 302
        assert Meeting.query.count() == 2
        clone = Meeting.query.get(2)
        assert len(clone.rules) == 1
        condition_clones = Condition.query.filter(Condition.rule.has(
            meeting=clone)).all()
        assert len(condition_clones) == 3
        for condition in condition_clones:
            assert condition.values.count() == 1
        action_clones = Action.query.filter(Action.rule.has(
            meeting=clone)).all()
        assert len(action_clones) == 2


def test_clone_meeting_participants_are_not_cloned(app, user):
    MEDIA_ENABLED = {'media_participant_enabled': True}
    category = MeetingCategoryFactory(meeting__settings=MEDIA_ENABLED,
                                      category_type=Category.MEDIA)
    meeting = category.meeting
    MediaParticipantFactory.create_batch(7, category=category)
    ParticipantFactory.create_batch(5, category=category)

    data = normalize_data(MeetingFactory.attributes())
    data['title-english'] = data.pop('title')
    data['venue_city-english'] = data.pop('venue_city')
    data['badge_header-english'] = data.pop('badge_header')
    data['photo_field_id'] = data['media_photo_field_id'] = '0'
    data['meeting_type_slug'] = meeting.meeting_type.slug

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('meetings.clone', meeting_id=meeting.id)
        resp = client.post(url, data=data)
        assert resp.status_code == 302
        assert Meeting.query.count() == 2
        clone = Meeting.query.get(2)
        assert clone.participants.count() == 0


def check_translations_are_equal(original, clone):
    assert original is not clone
    assert original.english is not clone.english
    assert original.english == clone.english
    assert (original.french == clone.french == None or
            original.french is not clone.french)
    assert (original.french or '') == (clone.french or '')
    assert (original.spanish == clone.spanish == None or
            original.spanish is not clone.spanish)
    assert (original.spanish or '') == (clone.spanish or '')


def check_fields_are_equal(original, clone):
    assert original is not clone
    assert original.slug is not clone.slug
    assert original.slug == clone.slug
    check_translations_are_equal(original.label, clone.label)
    assert (original.description == clone.description == None or
            original.description is not clone.description)
    assert original.description == clone.description
    assert original.field_type is not clone.field_type
    assert original.field_type == clone.field_type
    assert original.required == clone.required
    assert original.is_primary == clone.is_primary
    assert (original.visible_on_registration_form ==
            clone.visible_on_registration_form)
    assert original.sort == clone.sort
    assert original.custom_field_type is not clone.custom_field_type
    assert original.custom_field_type == clone.custom_field_type


def check_categories_are_equal(original, clone):
    assert original is not clone
    check_translations_are_equal(original.title, clone.title)
    assert original.color is not clone.color
    assert original.color == clone.color
    assert (original.background == clone.background == None or
            original.background is not clone.background)
    assert original.background == clone.background
    assert original.representing is not clone.representing
    assert original.representing == clone.representing
    assert original.category_type is not clone.category_type
    assert original.category_type == clone.category_type
    assert original.group is not clone.group
    assert original.group == clone.group
    assert original.sort == clone.sort
    assert (original.visible_on_registration_form ==
            clone.visible_on_registration_form)
