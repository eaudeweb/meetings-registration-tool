from flask import url_for
from pyquery import PyQuery
from StringIO import StringIO
from py.path import local

from mrt.mail import mail
from mrt.models import Participant, ActivityLog, User, CustomFieldValue
from .factories import MeetingCategoryFactory, ParticipantFactory
from .factories import StaffFactory, RoleUserMeetingFactory, UserFactory
from .factories import UserNotificationFactory, CustomFieldFactory

from testsuite.utils import add_participant_custom_fields
from testsuite.utils import populate_participant_form


def test_meeting_online_resistration_open(app, default_meeting):
    category = MeetingCategoryFactory(meeting__online_registration=True)

    client = app.test_client()
    with app.test_request_context():
        add_participant_custom_fields(category.meeting)
        resp = client.get(url_for('meetings.registration',
                                  meeting_id=category.meeting.id))
        assert PyQuery(resp.data)('form').length == 1


def test_meeting_online_registration_closed(app, default_meeting):
    category = MeetingCategoryFactory(meeting__online_registration=False)

    client = app.test_client()
    with app.test_request_context():
        add_participant_custom_fields(category.meeting)
        resp = client.get(url_for('meetings.registration',
                                  meeting_id=category.meeting.id))
        html = PyQuery(resp.data)
        assert html('form').length == 0
        assert html('.alert').length == 1


def test_meeting_online_registration_add(app, default_meeting):
    category = MeetingCategoryFactory(meeting__online_registration=True)
    meeting = category.meeting
    role_user = RoleUserMeetingFactory(meeting=meeting)
    RoleUserMeetingFactory(meeting=meeting,
                           user__email='test@email.com')
    StaffFactory(user=role_user.user)
    UserNotificationFactory(user=role_user.user, meeting=meeting)

    data = ParticipantFactory.attributes()
    data['category_id'] = category.id

    client = app.test_client()
    with app.test_request_context(), mail.record_messages() as outbox:
        resp = register_participant_online(client, data, meeting)
        assert resp.status_code == 200
        assert Participant.query.filter_by(meeting=meeting).count() == 1
        assert len(outbox) == 2
        assert ActivityLog.query.filter_by(meeting=meeting).count() == 1


def test_meeting_online_registration_with_meeting_photo(app, default_meeting):
    category = MeetingCategoryFactory(meeting__online_registration=True)
    meeting = category.meeting
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


def test_meeting_online_registration_and_user_creation(app, default_meeting):
    category = MeetingCategoryFactory(meeting__online_registration=True)
    meeting = category.meeting

    data = ParticipantFactory.attributes()
    data['category_id'] = category.id
    client = app.test_client()
    with app.test_request_context():
        resp = register_participant_online(client, data, meeting)
        assert resp.status_code == 200
        assert Participant.query.filter_by(meeting=meeting).count() == 1

        participant = Participant.query.filter_by(meeting=meeting).first()
        resp = create_user_after_registration(client, participant, meeting)
        assert resp.status_code == 200
        assert User.query.count() == 1
        assert participant.user is User.query.get(1)


def test_meeting_online_registration_default_participant_creation(app, default_meeting):
    category = MeetingCategoryFactory(meeting__online_registration=True)
    meeting = category.meeting
    data = ParticipantFactory.attributes()
    data['category_id'] = category.id

    client = app.test_client()
    with app.test_request_context():
        register_participant_online(client, data, meeting)
        participant = Participant.query.filter_by(meeting=meeting).first()
        create_user_after_registration(client, participant, meeting)

        default_participant = participant.user.get_default()
        assert default_participant is not None
        assert_participants_fields_equal(participant, default_participant)


def test_meeting_online_registration_default_participant_update(app, default_meeting):
    category = MeetingCategoryFactory(meeting__online_registration=True)
    meeting = category.meeting
    data = ParticipantFactory.attributes()
    data['category_id'] = category.id

    client = app.test_client()
    with app.test_request_context():
        register_participant_online(client, data, meeting)
        participant = Participant.query.filter_by(meeting=meeting).first()
        create_user_after_registration(client, participant, meeting)

        default_participant = participant.user.get_default()

    new_category = MeetingCategoryFactory(meeting__online_registration=True)
    new_meeting = new_category.meeting
    data['first_name'] = 'Johny'
    data['category_id'] = new_category.id

    with app.test_request_context():
        resp = register_participant_online(client, data, new_meeting,
                                           participant.user)

        assert resp.status_code == 200
        assert Participant.query.filter_by(meeting=new_meeting).count() == 1
        assert default_participant.first_name == 'Johny'


def test_meeting_registration_default_participant_custom_fields(app, default_meeting):
    category = MeetingCategoryFactory(meeting__online_registration=True)
    meeting = category.meeting
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

        default_participant = participant.user.get_default()
        assert (default_participant.custom_field_values.count() ==
                participant.custom_field_values.count())
        for cfv in default_participant.custom_field_values.all():
            assert cfv.custom_field.meeting is default_meeting
            participant_cfv = (participant.custom_field_values
                               .filter(CustomFieldValue.custom_field
                                       .has(slug=cfv.custom_field.slug))
                               .first())
            assert cfv.value == participant_cfv.value


def test_meeting_registration_default_participant_photo(app, default_meeting):
    category = MeetingCategoryFactory(meeting__online_registration=True)
    meeting = category.meeting
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

        default_participant = participant.user.get_default()
        photo_field = participant.custom_field_values.scalar().value
        default_photo_field = (default_participant.custom_field_values
                               .scalar().value)
        assert photo_field != default_photo_field
        assert upload_dir.join(default_photo_field).check()

def test_meeting_registration_default_participant_custom_fields_update(app, default_meeting):
    category = MeetingCategoryFactory(meeting__online_registration=True)
    meeting = category.meeting
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

    new_category = MeetingCategoryFactory(meeting__online_registration=True)
    new_meeting = new_category.meeting
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
        default_participant = participant.user.get_default()
        assert (default_participant.custom_field_values.count() ==
                participant.custom_field_values.count() + 2)
        for cfv in participant.custom_field_values:
            default_participant_cfv = (
                default_participant.custom_field_values
                                   .filter(CustomFieldValue.custom_field
                                           .has(slug=cfv.custom_field.slug))
                                   .first())
            assert default_participant_cfv.custom_field.meeting is default_meeting
            assert cfv.value == default_participant_cfv.value


def test_meeting_online_registration_is_prepopulated(app, default_meeting):
    category = MeetingCategoryFactory(meeting__online_registration=True)
    meeting = category.meeting
    user = UserFactory()
    part = ParticipantFactory(user=user, meeting=default_meeting,
                              category=None)

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        add_participant_custom_fields(meeting)
        resp = client.get(url_for('meetings.registration',
                                  meeting_id=meeting.id))
        assert resp.status_code == 200
        html = PyQuery(resp.data)
        assert part.title.value == html('#title option[selected]').val()
        assert part.first_name == html('#first_name').val()
        assert part.last_name == html('#last_name').val()
        assert part.email == html('#email').val()
        assert part.language.value == html('#language option[selected]').val()
        assert part.country.code == html('#country option[selected]').val()


def register_participant_online(client, participant_data, meeting, user=None):
    """Helper function that registers a participant to a meeting."""
    if user:
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
    add_participant_custom_fields(meeting)
    populate_participant_form(meeting, participant_data)
    resp = client.post(url_for('meetings.registration',
                       meeting_id=meeting.id), data=participant_data)
    return resp


def create_user_after_registration(client, participant, meeting):
    """Helper function that creates a user after the participant registered."""
    data = {
        'email': participant.email,
        'password': 'testpassword',
        'confirm': 'testpassword'
    }
    resp = client.post(url_for('meetings.registration_user',
                               meeting_id=meeting.id), data=data)
    return resp


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
