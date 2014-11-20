from mrt.forms.meetings.meeting import ParticipantDummyForm
from mrt.forms.meetings.meeting import _CUSTOM_FIELD_MAPPER
from mrt.models import CustomField, CustomFieldChoice, Translation, db


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
        data[custom_field.slug] = (
            custom_field.custom_field_choices.first().value)
    data['represented_country'] = 'RO'
