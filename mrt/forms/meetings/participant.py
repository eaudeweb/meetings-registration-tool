from flask import g

from wtforms import fields
from wtforms.validators import DataRequired

from mrt.forms.base import BaseForm
from mrt.models import db
from mrt.models import Participant, Category


class ParticipantEditForm(BaseForm):

    category_id = fields.SelectField(validators=(DataRequired(),),
                                     coerce=int, choices=[])

    class Meta:
        model = Participant

    def __init__(self, *args, **kwargs):
        super(ParticipantEditForm, self).__init__(*args, **kwargs)
        query = Category.query.filter_by(meeting_id=g.meeting.id)
        self.category_id.choices = [(c.id, c.title) for c in query]

    def save(self):
        participant = self.obj or Participant()
        self.populate_obj(participant)
        participant.meeting_id = g.meeting.id
        if participant.id is None:
            db.session.add(participant)
        db.session.commit()
        return participant
