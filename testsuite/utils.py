import time
from base64 import b64encode

from flask import url_for

from mrt.forms.meetings.meeting import ParticipantDummyForm
from mrt.forms.meetings.meeting import _CUSTOM_FIELD_MAPPER
from mrt.models import CustomField, CustomFieldChoice, Translation, db
from mrt.models import Meeting

from .factories import MeetingTypeFactory, MeetingFactory, normalize_data


def add_participant_custom_fields(meeting):
    """Adds participants fields as CustomFields to meeting."""
    for i, field in enumerate(ParticipantDummyForm()):
        custom_field = CustomField()
        custom_field.meeting = meeting
        custom_field.slug = field.name
        custom_field.label = Translation(english=unicode(field.label.text))
        custom_field.required = field.flags.required
        custom_field.field_type = _CUSTOM_FIELD_MAPPER[field.type]
        custom_field.is_primary = True
        custom_field.sort = i + 1
        custom_field.visible_on_registration_form = True
        db.session.add(custom_field)

        if custom_field.field_type == CustomField.SELECT:
            _add_choice_values_for_custom_field(
                custom_field, field.choices)
    db.session.commit()


def _add_choice_values_for_custom_field(custom_field, choices):
    """Adds CustomFieldChoices for CustomField."""
    for value, label in (choices or []):
        custom_field_choice = CustomFieldChoice(custom_field=custom_field)
        custom_field_choice.value = Translation(english=value)
        db.session.add(custom_field_choice)


def populate_participant_form(meeting, data={}):
    """Populate data dict with value from CustomFieldChoice."""
    custom_fields = CustomField.query.filter_by(meeting=meeting,
                                                is_primary=True,
                                                field_type=CustomField.SELECT)

    for custom_field in custom_fields:
        data[custom_field.slug] = custom_field.choices.first().value
    data['represented_country'] = 'RO'
    now = int(time.time())
    data['ts'] = b64encode(str(now))


def add_new_meeting(app, user):
    """Adds a new meeting."""
    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id

        meeting_type = MeetingTypeFactory()
        meeting_type.load_default_phrases()
        data = normalize_data(MeetingFactory.attributes())
        data['title-english'] = data.pop('title')
        data['acronym'] = acronym = data.pop('acronym')
        data['venue_city-english'] = data.pop('venue_city')
        data['badge_header-english'] = data.pop('badge_header')
        data['online_registration'] = 'y'
        data['photo_field_id'] = '0'
        data['address_field_id'] = '0'
        data['telephone_field_id'] = '0'
        data['media_photo_field_id'] = '0'
        data['settings'] = 'media_participant_enabled'
        data['meeting_type_slug'] = meeting_type.slug

        url = url_for('meetings.add')
        resp = client.post(url, data=data)

        assert resp.status_code == 302
        return Meeting.query.filter_by(acronym=acronym).first()


def add_multicheckbox_field(client, meeting, data, custom_field_id=None,
                            status_code=302):
    resp = client.post(url_for('meetings.custom_field_edit',
                               meeting_id=meeting.id,
                               custom_field_type=CustomField.PARTICIPANT,
                               custom_field_id=custom_field_id),
                       data=data)
    assert resp.status_code == status_code
