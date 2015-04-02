from flask import url_for
from pyquery import PyQuery
from StringIO import StringIO
from py.path import local

from mrt.mail import mail
from mrt.models import Participant, ActivityLog, User, CustomFieldValue
from mrt.models import Category, CustomField, Phrase
from mrt.forms.meetings import add_custom_fields_for_meeting
from mrt.forms.meetings import MediaParticipantDummyForm
from .factories import MeetingCategoryFactory, ParticipantFactory
from .factories import RoleUserMeetingFactory, UserFactory
from .factories import UserNotificationFactory, CustomFieldFactory
from .factories import MediaParticipantFactory, DocumentFieldFactory

from testsuite.utils import populate_participant_form, add_new_meeting


def test_meeting_resistration_open(app, default_meeting):
    category = MeetingCategoryFactory(meeting__online_registration=True)

    client = app.test_client()
    with app.test_request_context():
        add_custom_fields_for_meeting(category.meeting)
        resp = client.get(url_for('meetings.registration',
                                  meeting_acronym=category.meeting.acronym))
        assert PyQuery(resp.data)('form').length == 1


def test_meeting_registration_closed(app, default_meeting):
    category = MeetingCategoryFactory(meeting__online_registration=False)

    client = app.test_client()
    with app.test_request_context():
        add_custom_fields_for_meeting(category.meeting)
        resp = client.get(url_for('meetings.registration',
                                  meeting_acronym=category.meeting.acronym))
        html = PyQuery(resp.data)
        assert html('form').length == 0
        assert html('.alert').length == 1


def test_meeting_registration_add(app, user, default_meeting):
    meeting = add_new_meeting(app, user)
    category = MeetingCategoryFactory(meeting=meeting)
    role_user = RoleUserMeetingFactory(meeting=meeting)
    RoleUserMeetingFactory(meeting=meeting, user__email='test@email.com')
    UserNotificationFactory(user=role_user.user, meeting=meeting)

    data = ParticipantFactory.attributes()
    data['category_id'] = category.id

    client = app.test_client()
    with app.test_request_context(), mail.record_messages() as outbox:
        resp = register_participant_online(client, data, meeting)
        assert resp.status_code == 200
        assert Participant.query.filter_by(meeting=meeting).count() == 1
        participant = Participant.query.get(1)
        assert participant.participant_type.code == Participant.PARTICIPANT
        assert len(outbox) == 3
        assert ActivityLog.query.filter_by(meeting=meeting).count() == 1


def test_meeting_registration_success_phrases(app, user, default_meeting):
    meeting = add_new_meeting(app, user)
    category = MeetingCategoryFactory(meeting=meeting)
    online_phrase = meeting.phrases.filter_by(group=Phrase.ONLINE_CONFIRMATION,
                                              name=Phrase.PARTICIPANT).scalar()
    online_phrase.description.english = 'Online success message'
    email_phrase = meeting.phrases.filter_by(group=Phrase.EMAIL_CONFIRMATION,
                                             name=Phrase.PARTICIPANT).scalar()
    email_phrase.description.english = 'Email success message'

    data = ParticipantFactory.attributes()
    data['category_id'] = category.id

    client = app.test_client()
    with app.test_request_context(), mail.record_messages() as outbox:
        resp = register_participant_online(client, data, meeting)
        assert resp.status_code == 200
        success_message = PyQuery(resp.data)('h4').text()
        assert success_message == online_phrase.description.english
        assert Participant.query.filter_by(meeting=meeting).count() == 1
        participant = Participant.query.get(1)
        assert participant.participant_type.code == Participant.PARTICIPANT
        assert len(outbox) == 2
        success_message = PyQuery(outbox[1].html)('h4').text()
        assert success_message == email_phrase.description.english


def test_meeting_registration_media_add(app, user, default_meeting):
    meeting = add_new_meeting(app, user)
    category = MeetingCategoryFactory(meeting=meeting,
                                      category_type=Category.MEDIA)
    role_user = RoleUserMeetingFactory(meeting=meeting)
    RoleUserMeetingFactory(meeting=meeting,
                           user__email='test@email.com')
    UserNotificationFactory(user=role_user.user, meeting=meeting,
                            notification_type='notify_media_participant')

    data = MediaParticipantFactory.attributes()
    data['category_id'] = category.id
    client = app.test_client()
    with app.test_request_context(), mail.record_messages() as outbox:
        resp = register_media_participant_online(client, data, meeting)
        assert resp.status_code == 200
        assert Participant.query.filter_by(meeting=meeting).count() == 1
        participant = Participant.query.get(1)
        assert participant.participant_type.code == Participant.MEDIA
        assert len(outbox) == 3
        assert ActivityLog.query.filter_by(meeting=meeting).count() == 1


def test_meeting_media_registration_default_participant_custom_fields(
        app, default_meeting, user):
    meeting = add_new_meeting(app, user)
    category = MeetingCategoryFactory(meeting=meeting,
                                      category_type=Category.MEDIA)
    CustomFieldFactory(field_type='text', meeting=meeting,
                       label__english='size',
                       custom_field_type=CustomField.MEDIA)
    CustomFieldFactory(field_type='checkbox', meeting=meeting,
                       label__english='passport',
                       custom_field_type=CustomField.MEDIA)

    data = MediaParticipantFactory.attributes()
    data['category_id'] = category.id
    data['size'] = 40
    data['passport'] = 'y'

    client = app.test_client()
    with app.test_request_context():
        resp = register_media_participant_online(client, data, meeting)
        assert resp.status_code == 200
        part = Participant.query.current_meeting().media_participants().first()
        create_user_after_registration(client, part, meeting)
        assert (default_meeting.custom_fields
                .filter_by(custom_field_type='media', is_primary=False)
                .count() == 2)

        default_participant = part.user.get_default(Participant.DEFAULT_MEDIA)
        assert (default_participant.custom_field_values.count() ==
                part.custom_field_values.count())
        for cfv in default_participant.custom_field_values.all():
            assert cfv.custom_field.meeting is default_meeting
            participant_cfv = (part.custom_field_values
                               .filter(CustomFieldValue.custom_field
                                       .has(slug=cfv.custom_field.slug))
                               .first())
            assert cfv.value == participant_cfv.value


def test_meeting_registration_with_meeting_photo(app, user, default_meeting):
    meeting = add_new_meeting(app, user)
    category = MeetingCategoryFactory(meeting=meeting)
    photo_field = CustomFieldFactory(meeting=meeting)
    meeting.photo_field = photo_field

    data = ParticipantFactory.attributes()
    data['category_id'] = category.id
    data[photo_field.slug] = (StringIO('Test'), 'test.png')
    upload_dir = local(app.config['UPLOADED_CUSTOM_DEST'])

    client = app.test_client()
    with app.test_request_context():
        resp = register_participant_online(client, data, meeting)
        assert resp.status_code == 200
        participant = Participant.query.filter_by(meeting=meeting).first()
        assert participant.photo is not None
        assert upload_dir.join(participant.photo).check()
        assert participant.participant_type.code == Participant.PARTICIPANT


def test_meeting_registration_and_user_creation(app, user, default_meeting):
    meeting = add_new_meeting(app, user)
    category = MeetingCategoryFactory(meeting=meeting)

    data = ParticipantFactory.attributes()
    data['category_id'] = category.id
    client = app.test_client()
    with app.test_request_context():
        resp = register_participant_online(client, data, meeting)
        assert resp.status_code == 200
        assert Participant.query.filter_by(meeting=meeting).count() == 1

        participant = Participant.query.filter_by(meeting=meeting).first()
        resp = create_user_after_registration(client, participant, meeting)
        assert resp.status_code == 302
        assert User.query.count() == 2
        assert participant.user is User.query.get(2)


def test_meeting_registration_user_success_details(app, user, default_meeting):
    meeting = add_new_meeting(app, user)
    category = MeetingCategoryFactory(meeting=meeting)

    data = ParticipantFactory.attributes()
    data['category_id'] = category.id
    client = app.test_client()
    with app.test_request_context():
        resp = register_participant_online(client, data, meeting)
        assert resp.status_code == 200
        assert Participant.query.filter_by(meeting=meeting).count() == 1

        participant = Participant.query.filter_by(meeting=meeting).first()
        resp = create_user_after_registration(client, participant, meeting,
                                              follow=True)
        assert resp.status_code == 200
        html = PyQuery(resp.data)
        assert (html('td[for="category_id"]').text() ==
                participant.category.title.english)
        assert html('td[for="email"]').text() == participant.email
        assert html('td[for="title"]').text() == participant.title.value
        assert html('td[for="first_name"]').text() == participant.first_name
        assert html('td[for="last_name"]').text() == participant.last_name
        assert html('td[for="language"]').text() == participant.language.value
        assert html('td[for="country"]').text() == participant.country.name
        assert (html('td[for="represented_country"]').text() ==
                participant.represented_country.name)


def test_meeting_registration_media_user_success_details(app, user,
                                                         default_meeting):
    meeting = add_new_meeting(app, user)
    category = MeetingCategoryFactory(meeting=meeting,
                                      category_type=Category.MEDIA)

    data = MediaParticipantFactory.attributes()
    data['category_id'] = category.id
    client = app.test_client()
    with app.test_request_context():
        resp = register_media_participant_online(client, data, meeting)
        assert resp.status_code == 200
        assert Participant.query.filter_by(meeting=meeting).count() == 1

        participant = Participant.query.filter_by(meeting=meeting).first()
        resp = create_user_after_registration(client, participant, meeting,
                                              follow=True)
        assert resp.status_code == 200
        html = PyQuery(resp.data)
        assert (html('td[for="category_id"]').text() ==
                participant.category.title.english)
        assert html('td[for="email"]').text() == participant.email
        assert html('td[for="title"]').text() == participant.title.value
        assert html('td[for="first_name"]').text() == participant.first_name
        assert html('td[for="last_name"]').text() == participant.last_name


def test_meeting_registration_with_multiple_emails(app, user, default_meeting):
    meeting = add_new_meeting(app, user)
    category = MeetingCategoryFactory(meeting=meeting)

    data = ParticipantFactory.attributes()
    data['category_id'] = category.id
    data['email'] = 'john@test.com, johny@test.com'
    client = app.test_client()
    with app.test_request_context():
        resp = register_participant_online(client, data, meeting)
        assert resp.status_code == 200
        assert Participant.query.filter_by(meeting=meeting).count() == 1

        participant = Participant.query.filter_by(meeting=meeting).first()
        resp = create_user_after_registration(client, participant, meeting)
        assert resp.status_code == 200
        assert User.query.count() == 1
        html = PyQuery(resp.data)
        assert html('.text-danger small').length == 1


def test_meeting_registration_default_participant_creation(app, user,
                                                           default_meeting):
    meeting = add_new_meeting(app, user)
    category = MeetingCategoryFactory(meeting=meeting)
    data = ParticipantFactory.attributes()
    data['category_id'] = category.id

    client = app.test_client()
    with app.test_request_context():
        register_participant_online(client, data, meeting)
        participant = Participant.query.filter_by(meeting=meeting).first()
        create_user_after_registration(client, participant, meeting)

        default_participant = participant.user.get_default(
            Participant.DEFAULT)
        assert default_participant is not None
        assert_participants_fields_equal(participant, default_participant)
        assert default_participant.participant_type.code == Participant.DEFAULT
        assert default_participant.meeting_id != participant.meeting_id
        assert default_participant.meeting_id == default_meeting.id
        assert default_participant.category_id is None
        assert default_participant.registration_token is None


def test_meeting_registration_default_participant_update(app, user,
                                                         default_meeting):
    meeting = add_new_meeting(app, user)
    category = MeetingCategoryFactory(meeting=meeting)
    data = ParticipantFactory.attributes()
    data['category_id'] = category.id

    client = app.test_client()
    with app.test_request_context():
        register_participant_online(client, data, meeting)
        participant = Participant.query.filter_by(meeting=meeting).first()
        create_user_after_registration(client, participant, meeting)

        default_participant = participant.user.get_default(
            Participant.DEFAULT)

    new_meeting = add_new_meeting(app, user)
    new_category = MeetingCategoryFactory(meeting=new_meeting)
    data['first_name'] = 'Johny'
    data['category_id'] = new_category.id

    with app.test_request_context():
        register_participant_online(client, data, new_meeting,
                                    participant.user)
        assert Participant.query.filter_by(meeting=new_meeting).count() == 1
        assert default_participant.first_name == 'Johny'


def test_meeting_registration_default_participant_custom_fields(
        app, user, default_meeting):
    meeting = add_new_meeting(app, user)
    category = MeetingCategoryFactory(meeting=meeting)
    CustomFieldFactory(field_type='text', meeting=meeting,
                       label__english='size')
    CustomFieldFactory(field_type='checkbox', meeting=meeting,
                       label__english='passport')

    data = ParticipantFactory.attributes()
    data['category_id'] = category.id
    data['size'] = 40
    data['passport'] = 'y'

    client = app.test_client()
    with app.test_request_context():
        register_participant_online(client, data, meeting)
        participant = Participant.query.filter_by(meeting=meeting).first()
        create_user_after_registration(client, participant, meeting)

        default_participant = participant.user.get_default(
            Participant.DEFAULT)
        assert (default_participant.custom_field_values.count() ==
                participant.custom_field_values.count())
        for cfv in default_participant.custom_field_values.all():
            assert cfv.custom_field.meeting is default_meeting
            participant_cfv = (participant.custom_field_values
                               .filter(CustomFieldValue.custom_field
                                       .has(slug=cfv.custom_field.slug))
                               .first())
            assert cfv.value == participant_cfv.value


def test_meeting_registration_default_participant_photo(app, user,
                                                        default_meeting):
    meeting = add_new_meeting(app, user)
    category = MeetingCategoryFactory(meeting=meeting)
    photo_field = CustomFieldFactory(meeting=meeting)
    meeting.photo_field = photo_field
    upload_dir = local(app.config['UPLOADED_CUSTOM_DEST'])

    data = ParticipantFactory.attributes()
    data['category_id'] = category.id
    data[photo_field.slug] = (StringIO('Test'), 'test.png')

    client = app.test_client()
    with app.test_request_context():
        register_participant_online(client, data, meeting)
        participant = Participant.query.filter_by(meeting=meeting).first()
        create_user_after_registration(client, participant, meeting)

        default_participant = participant.user.get_default(
            Participant.DEFAULT)
        photo_field = participant.custom_field_values.scalar().value
        default_photo_field = (default_participant.custom_field_values
                               .scalar().value)
        assert photo_field != default_photo_field
        assert len(upload_dir.listdir()) == 2
        assert upload_dir.join(default_photo_field).check()


def test_meeting_registration_default_participant_custom_fields_update(
        app, user, default_meeting):
    meeting = add_new_meeting(app, user)
    category = MeetingCategoryFactory(meeting=meeting)
    photo_field = CustomFieldFactory(meeting=meeting)
    meeting.photo_field = photo_field
    CustomFieldFactory(field_type='text', meeting=meeting,
                       label__english='size')
    CustomFieldFactory(field_type='checkbox', meeting=meeting,
                       label__english='passport')

    data = ParticipantFactory.attributes()
    data['category_id'] = category.id
    data[photo_field.slug] = (StringIO('Test'), 'test.png')
    data['size'] = 40
    data['passport'] = 'y'

    client = app.test_client()
    with app.test_request_context():
        register_participant_online(client, data, meeting)
        participant = Participant.query.filter_by(meeting=meeting).first()
        create_user_after_registration(client, participant, meeting)

    new_meeting = add_new_meeting(app, user)
    new_category = MeetingCategoryFactory(meeting=new_meeting)
    CustomFieldFactory(field_type='text', meeting=new_meeting,
                       label__english='size')
    CustomFieldFactory(field_type='checkbox', meeting=new_meeting,
                       label__english='diet')
    data.pop(photo_field.slug)
    data['category_id'] = new_category.id
    data['size'] = 42
    data['diet'] = 'y'

    with app.test_request_context():
        resp = register_participant_online(client, data, new_meeting,
                                           participant.user)

        assert resp.status_code == 200
        participant = Participant.query.filter_by(meeting=new_meeting).first()
        default_participant = participant.user.get_default(
            Participant.DEFAULT)
        assert (default_participant.custom_field_values.count() ==
                participant.custom_field_values.count() + 2)
        for cfv in participant.custom_field_values:
            default_participant_cfv = (
                default_participant.custom_field_values
                                   .filter(CustomFieldValue.custom_field
                                           .has(slug=cfv.custom_field.slug))
                                   .first())
            assert (default_participant_cfv.custom_field.meeting
                    is default_meeting)
            assert cfv.value == default_participant_cfv.value


def test_meeting_registration_default_participant_photo_update(app, user,
                                                               default_meeting):
    meeting = add_new_meeting(app, user)
    category = MeetingCategoryFactory(meeting=meeting)
    photo_field = CustomFieldFactory(meeting=meeting)
    meeting.photo_field = photo_field
    upload_dir = local(app.config['UPLOADED_CUSTOM_DEST'])

    data = ParticipantFactory.attributes()
    data['category_id'] = category.id
    data[photo_field.slug] = (StringIO('Test'), 'test.png')

    client = app.test_client()
    with app.test_request_context():
        register_participant_online(client, data, meeting)
        participant = Participant.query.filter_by(meeting=meeting).first()
        create_user_after_registration(client, participant, meeting)
        default_participant = participant.user.get_default(
            Participant.DEFAULT)
        original_image = (default_participant.custom_field_values
                          .scalar().value)

    new_meeting = add_new_meeting(app, user)
    new_category = MeetingCategoryFactory(meeting=new_meeting)
    new_photo_field = CustomFieldFactory(meeting=new_meeting)
    data.pop(photo_field.slug)
    data[new_photo_field.slug] = (StringIO('Test'), 'test.png')
    data['category_id'] = new_category.id

    with app.test_request_context():
        resp = register_participant_online(client, data, new_meeting,
                                           participant.user)

        assert resp.status_code == 200
        participant = Participant.query.filter_by(meeting=new_meeting).first()
        default_participant = participant.user.get_default(
            Participant.DEFAULT)

        photo_field = participant.custom_field_values.scalar().value
        default_photo_field = (default_participant.custom_field_values
                               .scalar().value)
        assert photo_field != default_photo_field
        assert default_photo_field != original_image
        assert not upload_dir.join(original_image).check()
        assert upload_dir.join(default_photo_field).check()
        assert len(upload_dir.listdir()) == 3


def test_meeting_registration_is_prepopulated(app, user, default_meeting):
    meeting = add_new_meeting(app, user)
    MeetingCategoryFactory(meeting=meeting)
    user = UserFactory()
    part = ParticipantFactory(user=user, meeting=default_meeting,
                              category=None,
                              participant_type=Participant.DEFAULT)

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        add_custom_fields_for_meeting(default_meeting)
        add_custom_fields_for_meeting(meeting)
        resp = client.get(url_for('meetings.registration',
                                  meeting_acronym=meeting.acronym))
        assert resp.status_code == 200
        html = PyQuery(resp.data)
        assert part.title.value == html('#title option[selected]').val()
        assert part.first_name == html('#first_name').val()
        assert part.last_name == html('#last_name').val()
        assert part.email == html('#email').val()
        assert part.language.value == html('#language option[selected]').val()
        assert part.country.code == html('#country option[selected]').val()


def test_meeting_registration_multiple_email_user_form_prepopuluted(
        app, user, default_meeting):
    meeting = add_new_meeting(app, user)
    category = MeetingCategoryFactory(meeting=meeting)

    data = ParticipantFactory.attributes()
    data['category_id'] = category.id
    data['email'] = 'john@test.com, johny@test.com'
    client = app.test_client()
    with app.test_request_context():
        resp = register_participant_online(client, data, meeting)
        assert resp.status_code == 200
        assert Participant.query.filter_by(meeting=meeting).count() == 1
        populated_email = PyQuery(resp.data)('#email')[0].value
        assert populated_email == 'john@test.com'


def test_meeting_user_registration_is_not_accesible_logged_in(app, user):
    participant = ParticipantFactory()
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = create_user_after_registration(client, participant,
                                              participant.meeting)
        assert resp.status_code == 404


def test_meeting_registration_participant_and_media_on_same_user(
        app, user, default_meeting):
    meeting = add_new_meeting(app, user)
    category = MeetingCategoryFactory(meeting=meeting)
    media_category = MeetingCategoryFactory(meeting=meeting,
                                            category_type=Category.MEDIA)

    # FIRST REGISTER AS PARTICIPANT
    data = ParticipantFactory.attributes()
    data['category_id'] = category.id

    client = app.test_client()
    with app.test_request_context():
        resp = register_participant_online(client, data, meeting)
        assert resp.status_code == 200
        assert (meeting.participants
                .filter_by(participant_type=Participant.PARTICIPANT)
                .count() == 1)
        participant = meeting.participants.first()
        resp = create_user_after_registration(client, participant, meeting)
        assert resp.status_code == 302
        assert User.query.count() == 2
        user = User.query.get(2)

    # REGISTER AS MEDIA PARTICIPANT ON SAME USER
        data = MediaParticipantFactory.attributes()
        data['category_id'] = media_category.id
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = register_media_participant_online(client, data, meeting)
        assert resp.status_code == 200
        assert (meeting.participants
                .filter_by(participant_type=Participant.MEDIA)
                .count() == 1)
        media_participant = (meeting.participants
                             .filter_by(participant_type=Participant.MEDIA)
                             .first())

    # CHECK DEFAULT PARTICIPANT AND MEDIA CREATED
        assert user.get_default(Participant.DEFAULT) is not None
        assert user.get_default(Participant.DEFAULT_MEDIA) is not None

    # CHECK PARTICIPANT REGISTRATION FORM IS POPULATED
        resp = client.get(url_for('meetings.registration',
                                  meeting_acronym=meeting.acronym))
        assert resp.status_code == 200
        html = PyQuery(resp.data)
        assert participant.title.value == html('#title option[selected]').val()
        assert participant.first_name == html('#first_name').val()
        assert participant.last_name == html('#last_name').val()
        assert participant.email == html('#email').val()
        assert (participant.language.value ==
                html('#language option[selected]').val())
        assert (participant.country.code ==
                html('#country option[selected]').val())

    # CHECK MEDIA PARTICIPANT REGISTRATION FORM IS POPULATED
        resp = client.get(url_for('meetings.media_registration',
                                  meeting_acronym=meeting.acronym))
        assert resp.status_code == 200
        html = PyQuery(resp.data)
        assert (media_participant.title.value ==
                html('#title option[selected]').val())
        assert media_participant.first_name == html('#first_name').val()
        assert media_participant.last_name == html('#last_name').val()
        assert media_participant.email == html('#email').val()


def test_meeting_registration_timestamp_captcha(app, user, default_meeting):
    meeting = add_new_meeting(app, user)
    category = MeetingCategoryFactory(meeting=meeting)
    role_user = RoleUserMeetingFactory(meeting=meeting)
    RoleUserMeetingFactory(meeting=meeting, user__email='test@email.com')
    UserNotificationFactory(user=role_user.user, meeting=meeting)

    data = ParticipantFactory.attributes()
    data['category_id'] = category.id
    client = app.test_client()
    with app.test_request_context():
        app.config['DEBUG'] = False
        for i in range(4):
            resp = register_participant_online(client, data, meeting)
            assert resp.status_code == 200
    assert Participant.query.count() == 0


def test_meeting_registration_with_document_field(app, user):
    meeting = add_new_meeting(app, user)
    category = MeetingCategoryFactory(meeting=meeting)
    doc_field = DocumentFieldFactory(meeting=meeting)

    data = ParticipantFactory.attributes()
    data['category_id'] = category.id
    data[doc_field.slug] = (StringIO('Test'), 'test.pdf')
    upload_dir = local(app.config['UPLOADED_CUSTOM_DEST'])
    client = app.test_client()
    with app.test_request_context():
        resp = register_participant_online(client, data, meeting)
        assert resp.status_code == 200
        assert (meeting.participants
                .filter_by(participant_type=Participant.PARTICIPANT)
                .count() == 1)
        participant = meeting.participants.first()
        doc_field_value = (participant.custom_field_values
                           .filter_by(custom_field=doc_field).first())
        assert doc_field_value is not None
        assert upload_dir.join(doc_field_value.value).check()


def register_participant_online(client, participant_data, meeting, user=None):
    """Helper function that registers a participant to a meeting."""
    if user:
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
    add_custom_fields_for_meeting(meeting)
    populate_participant_form(meeting, participant_data)
    resp = client.post(url_for('meetings.registration',
                       meeting_acronym=meeting.acronym), data=participant_data)
    return resp


def register_media_participant_online(client, participant_data, meeting,
                                      user=None):
    if user:
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
    add_custom_fields_for_meeting(meeting,
                                  form_class=MediaParticipantDummyForm)
    populate_participant_form(meeting, participant_data)
    resp = client.post(url_for('meetings.media_registration',
                       meeting_acronym=meeting.acronym), data=participant_data)
    return resp


def create_user_after_registration(client, participant, meeting, follow=False):
    """Helper function that creates a user after the participant registered."""
    data = {
        'email': participant.email,
        'password': 'testpassword',
        'confirm': 'testpassword'
    }
    return client.post(url_for('meetings.registration_user',
                               meeting_id=meeting.id), data=data,
                       follow_redirects=follow)


def assert_participants_fields_equal(first, second):
    """Check if two participants have the same field values."""
    assert first.title == second.title
    assert first.first_name == second.first_name
    assert first.last_name == second.last_name
    assert first.email == second.email
    assert first.language == second.language
    assert first.country == second.country
    assert first.represented_country == second.represented_country
    assert first.represented_region == second.represented_region
    assert first.represented_organization == second.represented_organization
