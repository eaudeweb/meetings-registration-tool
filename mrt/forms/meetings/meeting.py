from flask import current_app as app
from flask.ext.login import current_user
from wtforms import fields, widgets
from wtforms.validators import ValidationError
from wtforms_alchemy import ModelFormField

from mrt.models import db, Meeting, Staff
from mrt.models import Phrase, PhraseDefault, Translation
from mrt.forms.base import BaseForm, TranslationInpuForm, MultiCheckboxField
from mrt.utils import copy_model_fields
from mrt.definitions import MEETING_SETTINGS


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

    title = ModelFormField(TranslationInpuForm, label='Description')
    badge_header = ModelFormField(TranslationInpuForm, label='Badge header')
    venue_city = ModelFormField(TranslationInpuForm, label='City')
    meeting_type = fields.SelectField('Meeting Type')
    owner_id = fields.SelectField('Owner', coerce=int)
    settings = MultiCheckboxField('Settings', choices=MEETING_SETTINGS)

    def __init__(self, *args, **kwargs):
        super(MeetingEditForm, self).__init__(*args, **kwargs)
        self.meeting_type.choices = app.config.get('MEETING_TYPES', [])
        self.owner_id.choices = [
            (x.id, x.full_name) for x in Staff.query.all()]
        if not self.owner_id.data:
            self.owner_id.data = current_user.staff.id

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

    def save(self):
        meeting = self.obj or Meeting()
        self.populate_obj(meeting)
        if meeting.id is None:
            db.session.add(meeting)
            self._save_phrases(meeting)
        db.session.commit()
        return meeting
