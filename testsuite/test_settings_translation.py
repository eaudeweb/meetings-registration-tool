from flask import url_for
from pyquery import PyQuery

from mrt.forms.meetings import add_custom_fields_for_meeting
from mrt.models import Meeting, CustomField, CategoryDefault, Phrase

from .factories import MeetingFactory, MeetingTypeFactory, normalize_data
from .factories import MeetingCategoryFactory, ParticipantFactory
from .factories import CustomFieldFactory, CategoryDefaultFactory
from .factories import PhraseDefaultFactory

from testsuite.utils import populate_participant_form, add_new_meeting


def test_meeting_add_with_no_spanish(app, user):
    data = normalize_data(MeetingFactory.attributes())
    meeting_type = MeetingTypeFactory()
    data['title-english'] = data.pop('title')
    data['title-spanish'] = 'Spanish title'
    data['venue_city-english'] = data.pop('venue_city')
    data['badge_header-english'] = data.pop('badge_header')
    data['badge_header-header'] = 'Spanish header'
    data['photo_field_id'] = data['media_photo_field_id'] = '0'
    data['meeting_type_slug'] = meeting_type.slug

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('meetings.add')
        resp = client.get(url)

        form = PyQuery(resp.data)('form.form-horizontal')
        assert len(form('input#title-english')) == 1
        assert len(form('input#title-french')) == 1
        assert len(form('input#title-spanish')) == 0

        assert len(form('input#badge_header-english')) == 1
        assert len(form('input#badge_header-french')) == 1
        assert len(form('input#badge_header-spanish')) == 0

        resp = client.post(url, data=data)

    assert resp.status_code == 302
    assert Meeting.query.count() == 1


def test_participant_add_working_language(app, user):
    category = MeetingCategoryFactory(meeting__owner=user.staff)
    meeting = category.meeting
    data = ParticipantFactory.attributes()
    data['category_id'] = category.id
    data['language'] = 'Spanish'

    client = app.test_client()
    with app.test_request_context():
        add_custom_fields_for_meeting(meeting)
        populate_participant_form(meeting, data)
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('meetings.participant_edit', meeting_id=meeting.id)

        resp = client.get(url)
        options = PyQuery(resp.data)('select#language option')
        assert len(options) == 3

        resp = client.post(url, data=data)
        assert resp.status_code == 200


def test_custom_field_add_label_language(app, user):
    meeting = MeetingFactory()
    data = CustomFieldFactory.attributes()
    data['label-english'] = data['label'].english
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.get(url_for('meetings.custom_field_edit',
                                  meeting_id=meeting.id,
                                  custom_field_type=CustomField.PARTICIPANT))

        form = PyQuery(resp.data)
        assert len(form('input#label-english')) == 1
        assert len(form('input#label-french')) == 1
        assert len(form('input#label-spanish')) == 0


def test_add_default_category_title_language(app, user):
    data = CategoryDefaultFactory.attributes()
    data = normalize_data(data)
    data['title-english'] = data.pop('title')
    data['title-spanish'] = 'Spanish title'

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.category_edit')
        resp = client.get(url)
        assert resp.status_code == 200

        form = PyQuery(resp.data)
        assert len(form('input#title-english')) == 1
        assert len(form('input#title-french')) == 1
        assert len(form('input#title-spanish')) == 0

        resp = client.post(url, data=data)
        assert resp.status_code == 302
        assert CategoryDefault.query.count() == 1


def test_add_default_phrase_description_language(app, user):
    phrase = PhraseDefaultFactory()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        url = url_for('admin.phrase_edit', meeting_type=phrase.meeting_type,
                      phrase_id=phrase.id)
        resp = client.get(url)

        description = PyQuery(resp.data)('.panel-body')

        assert len(description('#description-english')) == 1
        assert len(description('#description-spanish')) == 0


def test_meeting_registration_success_phrases(app, user, default_meeting):
    meeting = add_new_meeting(app, user)
    category = MeetingCategoryFactory(meeting=meeting)
    online_phrase = meeting.phrases.filter_by(
        group=Phrase.ONLINE_REGISTRATION,
        name=Phrase.PARTICIPANT).scalar()
    online_phrase.description.english = 'Online success message'
    online_phrase.description.french = 'Bonjour monsiuer online'
    email_phrase = meeting.phrases.filter_by(
        group=Phrase.EMAIL_CONFIRMATION,
        name=Phrase.FOR_PARTICIPANTS).scalar()
    email_phrase.description.english = 'Email success message'
    email_phrase.description.french = 'Bonjour monsiuer email'

    data = ParticipantFactory.attributes()
    data['category_id'] = category.id
    data['language'] = 'French'

    client = app.test_client()
    with app.test_request_context():
        add_custom_fields_for_meeting(meeting)
        populate_participant_form(meeting, data)
        resp = client.post(url_for('meetings.registration',
                                   meeting_acronym=meeting.acronym,
                                   lang='fr'),
                           data=data)
        assert resp.status_code == 200
        success_message = PyQuery(resp.data)('.text-center h4')
        assert success_message.text() == online_phrase.description.french

        data['language'] = 'English'
        resp = client.post(url_for('meetings.registration',
                                   meeting_acronym=meeting.acronym,
                                   lang='en'),
                           data=data)
        assert resp.status_code == 200
        success_message = PyQuery(resp.data)('.text-center h4')
        assert success_message.text() == online_phrase.description.english
