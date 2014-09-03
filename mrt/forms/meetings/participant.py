from flask import g

from wtforms import fields
from wtforms.validators import DataRequired

from mrt.forms.base import BaseForm
from mrt.models import db
from mrt.models import Participant, Category, MediaParticipant
from mrt.definitions import PRINTOUT_TYPES


class ParticipantEditForm(BaseForm):

    category_id = fields.SelectField('Category',
                                     validators=[DataRequired()],
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


class MediaParticipantEditForm(BaseForm):

    category_id = fields.SelectField('Category',
                                     validators=[DataRequired()],
                                     coerce=int, choices=[])

    class Meta:
        model = MediaParticipant

    def __init__(self, *args, **kwargs):
        super(MediaParticipantEditForm, self).__init__(*args, **kwargs)
        query = Category.query.filter_by(meeting_id=g.meeting.id)
        self.category_id.choices = [(c.id, c.title) for c in query]

    def save(self):
        media_participant = self.obj or MediaParticipant()
        self.populate_obj(media_participant)
        media_participant.meeting_id = g.meeting.id
        if media_participant.id is None:
            db.session.add(media_participant)
        db.session.commit()
        return media_participant


class BadgeCategories(BaseForm):

    categories = fields.SelectMultipleField()

    def __init__(self, *args, **kwargs):
        super(BadgeCategories, self).__init__(*args, **kwargs)
        categories = Category.query.filter_by(meeting=g.meeting)
        self.categories.choices = [(c.id, c.title) for c in categories]


class PrintoutForm(BadgeCategories):

    printout_type = fields.SelectField('Type', choices=PRINTOUT_TYPES)

