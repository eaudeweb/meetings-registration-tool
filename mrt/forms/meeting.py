from wtforms import Form, widgets
from wtforms_alchemy import model_form_factory
from wtforms_alchemy import ModelFormField

from mrt.models import db
from mrt.models import Meeting, Translation


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


class MeetingEditForm(ModelForm):

    class Meta:
        model = Meeting

    title = ModelFormField(TranslationInpuForm, label='Description')
