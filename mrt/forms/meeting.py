from wtforms import Form, fields, widgets
from wtforms_alchemy import model_form_factory
from wtforms_alchemy import ModelFormField

from mrt.models import db
from mrt.models import Meeting, MeetingType, Translation


BaseModelForm = model_form_factory(Form)


class ModelForm(BaseModelForm):

    @classmethod
    def get_session(self):
        return db.session


class TranslationInpuForm(ModelForm):

    class Meta:
        model = Translation
        field_args = {
            'english': {
                'widget': widgets.TextInput()
            },
            'french': {
                'widget': widgets.TextInput()
            },
            'spanish': {
                'widget': widgets.TextInput()
            }

        }


class MeetingTypeForm(ModelForm):

    slug = fields.SelectField('Type', choices=[])

    class Meta:
        model = MeetingType
        only = ('slug',)

    def __init__(self, *args, **kwargs):
        super(MeetingTypeForm, self).__init__(*args, **kwargs)
        self.slug.choices = (
            MeetingType.query
            .with_entities(MeetingType.slug, MeetingType.title)
            .all()
        )


class MeetingEditForm(ModelForm):

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
    meeting_type = ModelFormField(MeetingTypeForm)

    def save(self):
        pass
