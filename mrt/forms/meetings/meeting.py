from flask import current_app as app
from flask.ext.login import current_user
from wtforms import fields, widgets
from wtforms.validators import ValidationError
from wtforms_alchemy import ModelFormField

from mrt.models import db, Meeting, Staff, Participant
from mrt.models import Phrase, PhraseDefault, Translation
from mrt.models import CustomField, CustomFieldChoice

from mrt.forms.base import BaseForm, TranslationInputForm, MultiCheckboxField

from mrt.utils import copy_model_fields
from mrt.definitions import MEETING_SETTINGS


_CUSOMT_FIELD_MAPPER = {
    'StringField': CustomField.TEXT,
    'BooleanField': CustomField.CHECKBOX,
    'SelectField': CustomField.SELECT,
    'CountryField': CustomField.COUNTRY,
}


class MeetingEditForm(BaseForm):

    class Meta:
        model = Meeting
        field_args = {
            'venue_address': {
                'widget': widgets.TextArea()
            },
            'date_start': {
                'format': '%d.%m.%Y'
            },
            'date_end': {
                'format': '%d.%m.%Y'
            }
        }

    title = ModelFormField(TranslationInputForm, label='Description')
    badge_header = ModelFormField(TranslationInputForm, label='Badge header')
    venue_city = ModelFormField(TranslationInputForm, label='City')
    meeting_type = fields.SelectField('Meeting Type')
    owner_id = fields.SelectField('Owner', coerce=int)
    photo_field_id = fields.SelectField('Photo Field', coerce=int)
    settings = MultiCheckboxField('Settings', choices=MEETING_SETTINGS)

    def __init__(self, *args, **kwargs):
        super(MeetingEditForm, self).__init__(*args, **kwargs)
        self.meeting_type.choices = app.config.get('MEETING_TYPES', [])
        self.owner_id.choices = [
            (x.id, x.full_name or x.user.email) for x in Staff.query.all()]
        self.photo_field_id.choices = [(0, '-----')]
        if self.obj:
            query = self.obj.custom_fields.filter_by(field_type='image')
            image_fields = [(x.id, x.label) for x in query]
            self.photo_field_id.choices += image_fields
        if not self.owner_id.data:
            self.owner_id.data = current_user.staff.id

    def validate_photo_field_id(self, field):
        if field.data == 0:
            field.data = None

    def validate_settings(self, field):
        settings = dict(MEETING_SETTINGS)
        for key in field.data:
            if key not in settings:
                raise ValidationError("Setting doesn's exist")

    def _save_phrases(self, meeting):
        phrases_default = PhraseDefault.query.filter(
            PhraseDefault.meeting_type == meeting.meeting_type)
        for phrase_default in phrases_default:
            phrase = copy_model_fields(Phrase, phrase_default, exclude=(
                'id', 'description_id', 'meeting_type'))
            #Change english=phrase_default.translation.description.english
            descr = Translation(english=phrase_default.name)
            db.session.add(descr)
            phrase.description = descr
            phrase.meeting = meeting
            db.session.add(phrase)
            db.session.flush()

    def _add_custom_fields_for_meeting(self, meeting):
        for i, field in enumerate(ParticipantDummyForm()):
            custom_field = CustomField()
            custom_field.meeting = meeting
            custom_field.label = Translation(english=unicode(field.label.text))
            custom_field.required = field.flags.required
            custom_field.field_type = _CUSOMT_FIELD_MAPPER[field.type]
            custom_field.is_primary = True
            custom_field.sort = i + 1
            db.session.add(custom_field)

            if custom_field.field_type == CustomField.SELECT:
                self._add_choice_values_for_custom_field(
                    custom_field, field.choices)

        db.session.commit()

    def _add_choice_values_for_custom_field(self, custom_field, choices):
        for choice in choices:
            custom_field_choice = CustomFieldChoice(custom_field=custom_field)
            custom_field_choice.value = Translation(english=unicode(choice))
            db.session.add(custom_field_choice)

    def save(self):
        meeting = self.obj or Meeting()
        self.populate_obj(meeting)
        if meeting.id is None:
            db.session.add(meeting)
            self._save_phrases(meeting)
            self._add_custom_fields_for_meeting(meeting)
        db.session.commit()
        return meeting


class ParticipantDummyForm(BaseForm):

    class Meta:
        model = Participant
        exclude = ('deleted',)
