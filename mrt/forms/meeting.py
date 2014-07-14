from flask.ext.wtf import Form

from wtforms_alchemy import model_form_factory
from meetings.models import db
from meetings.models import Meeting


BaseModelForm = model_form_factory(Form)


class ModelForm(BaseModelForm):

    @classmethod
    def get_session(self):
        return db.session


class MeetingForm(ModelForm):

    class Meta:
        model = Meeting
