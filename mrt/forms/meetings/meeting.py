from flask import current_app as app
from wtforms import fields, widgets
from wtforms_alchemy import ModelFormField

from mrt.models import db, Meeting
from mrt.forms.base import BaseForm, TranslationInpuForm


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
    venue_city = ModelFormField(TranslationInpuForm, label='City')
    meeting_type = fields.SelectField('Meeting Type')

    def __init__(self, *args, **kwargs):
        super(MeetingEditForm, self).__init__(*args, **kwargs)
        self.meeting_type.choices = app.config.get('MEETING_TYPES', [])

    def save(self):
        meeting = self.obj or Meeting()
        self.populate_obj(meeting)
        if meeting.id is None:
            db.session.add(meeting)
        db.session.commit()
        return meeting
