from wtforms_alchemy import ModelForm

from mrt.models import db


class BaseForm(ModelForm):

    @classmethod
    def get_session(self):
        return db.session

    def __init__(self, *args, **kwargs):
        super(BaseForm, self).__init__(*args, **kwargs)
        self.obj = kwargs.get('obj', None)
