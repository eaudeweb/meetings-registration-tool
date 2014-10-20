from flask import g

from wtforms import fields
from wtforms.validators import DataRequired

from mrt.forms.base import BaseForm
from mrt.models import db
from mrt.models import Participant, Category, MediaParticipant
from mrt.definitions import PRINTOUT_TYPES


class ParticipantEditForm(BaseForm):

    def save(self, participant=None):
        participant = participant or Participant()
        participant.meeting_id = g.meeting.id

        for field_name, field in self._fields.items():
            cf = self._custom_fields[field.name]
            if cf.is_primary:
                value = field.data
                setattr(participant, field_name, value)
            else:
                cfv = cf.get_or_create_value(participant)
                cfv.value = field.data
                if not cfv.id:
                    db.session.add(cfv)

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
        query = Category.query.filter_by(meeting_id=g.meeting.id,
                                         category_type=Category.MEDIA)
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
