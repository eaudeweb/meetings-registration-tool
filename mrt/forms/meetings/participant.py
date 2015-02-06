import json
from collections import OrderedDict
from uuid import uuid4

from flask import g
from flask.ext.uploads import UploadSet, IMAGES
from werkzeug import FileStorage

from sqlalchemy import and_
from sqlalchemy_utils import Country
from wtforms import fields, compat
from wtforms.meta import DefaultMeta
from wtforms.validators import DataRequired

from mrt.definitions import PRINTOUT_TYPES
from mrt.forms.base import BaseForm
from mrt.models import db, Participant, Category, Action, Condition
from mrt.utils import unlink_participant_photo


custom_upload = UploadSet('custom', IMAGES)


class _RulesMixin(object):

    def _normalize_data(self, data):
        if isinstance(data, Country):
            return data.code
        return unicode(data)

    def _validate_conditions(self, rule):
        for condition in rule.conditions.all():
            values = [unicode(i.value) for i in condition.values.all()]
            field = self._fields[condition.field.slug]
            if self._normalize_data(field.data) not in values:
                return False
        return True

    def _validate_actions(self, rule):
        success = True
        for action in rule.actions.all():
            field = self._fields[action.field.slug]
            if action.is_required:
                if not field.validate(self, [DataRequired()]):
                    success = False
        return success

    def validate(self, **kwargs):
        success = super(_RulesMixin, self).validate(**kwargs)
        if not success:
            return success
        for rule in self.rules:
            conditions_validated = self._validate_conditions(rule)
            if conditions_validated:
                success = self._validate_actions(rule)
        return success


class _RulesMeta(DefaultMeta):

    def wrap_formdata(self, form, formdata):
        self.form = form
        return super(_RulesMeta, self).wrap_formdata(form, formdata)

    def render_field(self, field, render_kw):
        action = (
            Action.query.filter(and_(
                Action.field.has(slug=field.name),
                Action.rule.has(meeting=g.meeting))).scalar())
        if action and action.is_visible:
            conditions = Condition.query.filter_by(rule=action.rule).all()
            data = {}
            for condition in conditions:
                data[condition.field.slug] = [i.value for i in
                                              condition.values.all()]
            render_kw.update({'data-rules': json.dumps(data)})
        return field.widget(field, **render_kw)


class BaseParticipantForm(_RulesMixin, BaseForm):

    Meta = _RulesMeta

    def filter(self, field_types=[]):
        fields = OrderedDict([
            (slug, field) for slug, field in self._fields.items()
            if slug in self._custom_fields and
            self._custom_fields[slug].field_type in field_types
        ])
        return iter(compat.itervalues(fields))

    def exclude(self, field_types):
        fields = OrderedDict([
            (slug, field) for slug, field in self._fields.items()
            if slug in self._custom_fields and
            self._custom_fields[slug].field_type not in field_types
        ])
        return iter(compat.itervalues(fields))

    def has(self, field_type):
        return len([f for f in self._fields
                    if self._custom_fields[f].field_type == field_type]) > 0

    def save(self, participant=None, commit=True):
        participant = participant or Participant()
        participant.meeting_id = g.meeting.id
        if participant.id is None:
            participant.participant_type = self.CUSTOM_FIELDS_TYPE
            db.session.add(participant)

        for field_name, field in self._fields.items():
            if field_name.endswith('_'):
                continue

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
                elif isinstance(field.data, Country):
                    cfv.value = field.data.code
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
