from flask import request
from wtforms_alchemy import ModelForm
from wtforms import widgets
from mrt.models import db, Translation


class BaseForm(ModelForm):

    @classmethod
    def get_session(self):
        return db.session

    def __init__(self, formdata=None, obj=None, **kwargs):
        if formdata:
            formdata = formdata.copy()
            if request.files:
                formdata.update(request.files)
        super(BaseForm, self).__init__(formdata=formdata, obj=obj, **kwargs)
        self.obj = obj


class TranslationInpuForm(BaseForm):

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
