from flask import g

from wtforms import fields
from wtforms.validators import DataRequired

from mrt.forms.base import BaseForm
from mrt.models import Participant, Category


class ParticipantEditForm(BaseForm):

    category = fields.SelectField(validators=(DataRequired(),),
                                  coerce=int, choices=[])

    class Meta:
        model = Participant

    def __init__(self, *args, **kwargs):
        super(ParticipantEditForm, self).__init__(*args, **kwargs)
        query = Category.query.filter_by(meeting_id=g.meeting.id)
        self.category.choices = [(c.id, c.title) for c in query]

    def save(self):
        pass
