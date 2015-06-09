import json
from collections import OrderedDict

from flask import g

from sqlalchemy import and_
from sqlalchemy_utils import Country
from wtforms import fields, compat
from wtforms.meta import DefaultMeta
from wtforms.validators import DataRequired

from mrt.definitions import PRINTOUT_TYPES
from mrt.forms.base import BaseForm
from mrt.models import db, Participant, Category, Action, Condition
from mrt.models import CustomField


class _RulesMixin(object):

    def _normalize_data(self, data):
        if isinstance(data, Country):
            return data.code
        if isinstance(data, bool):
            return 'true' if data else 'false'
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

    def render_field(self, field, render_kw):
        actions = (
            Action.query.filter(
                and_(
                    Action.field.has(slug=field.name),
                    Action.rule.has(meeting=g.meeting),
                    Action.is_visible == True
                )
            )
        )
        rules = []
        for action in actions:
            conditions = Condition.query.filter_by(rule=action.rule).all()
            if conditions:
                data = {}
                for c in conditions:
                    data[c.field.slug] = [i.value for i in c.values.all()]
                rules.append(data)
        if rules:
            render_kw.update({'data-rules': json.dumps(rules)})
        return field.widget(field, **render_kw)


class BaseParticipantForm(_RulesMixin, BaseForm):

    Meta = _RulesMeta

    def __init__(self, *args, **kwargs):
        obj = kwargs.get('obj', None)
        super(BaseParticipantForm, self).__init__(*args, **kwargs)
        if obj:
            participant = getattr(obj, '_participant', None)
            for field_name, field in self._fields.items():
                setattr(field, '_participant', participant)

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
        return bool([f for f in self._fields if f in self._custom_fields and
                    self._custom_fields[f].field_type == field_type])

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
                setattr(participant, field_name, field.data)
            elif field.data is not None:
                field.save(cf, participant)

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
        categories = Category.query.filter_by(
            meeting=g.meeting,
            category_type=Category.PARTICIPANT)
        self.categories.choices = [(c.id, c.title) for c in categories]


class PrintoutForm(BadgeCategories):

    printout_type = fields.SelectField('Type', choices=PRINTOUT_TYPES)


class FlagForm(BaseForm):

    flag = fields.SelectField()

    def __init__(self, *args, **kwargs):
        super(FlagForm, self).__init__(*args, **kwargs)
        flags = g.meeting.custom_fields.filter_by(
            field_type=CustomField.CHECKBOX,
            is_primary=True)
        self.flag.choices = [('', '---')] + [(f.slug, f.label) for f in flags]


class EventsForm(BaseForm):

    events = fields.SelectMultipleField()

    def __init__(self, *args, **kwargs):
        super(EventsForm, self).__init__(*args, **kwargs)
        events = g.meeting.custom_fields.filter_by(
            field_type=CustomField.EVENT)
        self.events.choices = [(e.id, e.label) for e in events]
