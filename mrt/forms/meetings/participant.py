from collections import OrderedDict
from uuid import uuid4

from flask import g
from flask.ext.uploads import UploadSet, IMAGES
from werkzeug import FileStorage
from wtforms import fields, compat

from mrt.definitions import PRINTOUT_TYPES
from mrt.forms.base import BaseForm
from mrt.models import db, Participant, Category
from mrt.utils import unlink_participant_photo


custom_upload = UploadSet('custom', IMAGES)


class BaseParticipantForm(BaseForm):

    def filter(self, field_types=[]):
        fields = OrderedDict([
            (slug, field) for slug, field in self._fields.items()
            if self._custom_fields[slug].field_type in field_types
        ])
        return iter(compat.itervalues(fields))

    def exclude(self, field_types):
        fields = OrderedDict([
            (slug, field) for slug, field in self._fields.items()
            if self._custom_fields[slug].field_type not in field_types
        ])
        return iter(compat.itervalues(fields))

    def has(self, field_type):
        return len([f for f in self._fields
                    if self._custom_fields[f].field_type == field_type]) > 0

    def save(self, participant=None, commit=True):
        participant = participant or Participant()
        participant.meeting_id = g.meeting.id
        if participant.id is None:
            # TODO this should be only on registration
            participant.registration_token = str(uuid4())
            participant.participant_type = self.CUSTOM_FIELDS_TYPE
            db.session.add(participant)

        for field_name, field in self._fields.items():
            cf = self._custom_fields[field.name]
            if cf.is_primary:
                value = field.data
                setattr(participant, field_name, value)
            elif field.data:
                cfv = cf.get_or_create_value(participant)
                if isinstance(field.data, FileStorage):
                    current_filename = cfv.value
                    cfv.value = custom_upload.save(
                        field.data, name=str(uuid4()) + '.')
                    unlink_participant_photo(current_filename)
                else:
                    cfv.value = field.data
                if not cfv.id:
                    db.session.add(cfv)
        if commit:
            db.session.commit()

        return participant


class ParticipantEditForm(BaseParticipantForm):

    CUSTOM_FIELDS_TYPE = 'participant'


class MediaParticipantEditForm(ParticipantEditForm):

    CUSTOM_FIELDS_TYPE = 'media'


class BadgeCategories(BaseForm):

    categories = fields.SelectMultipleField()

    def __init__(self, *args, **kwargs):
        super(BadgeCategories, self).__init__(*args, **kwargs)
        categories = Category.query.filter_by(meeting=g.meeting)
        self.categories.choices = [(c.id, c.title) for c in categories]


class PrintoutForm(BadgeCategories):

    printout_type = fields.SelectField('Type', choices=PRINTOUT_TYPES)
