import json
from collections import OrderedDict

from flask import g
from flask import current_app as app

from sqlalchemy import and_
from wtforms import fields, compat
from wtforms.meta import DefaultMeta
from wtforms.validators import DataRequired, ValidationError

from mrt.custom_country import Country
from mrt.definitions import PRINTOUT_TYPES
from mrt.forms.base import BaseForm
from mrt.models import db, Participant, Action, Condition
from mrt.models import CustomField
from mrt.models import CategoryTag, Category
from mrt.utils import crop_file
from mrt.utils import unlink_thumbnail_file
from mrt.utils import unlink_uploaded_file


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
            field = self._fields.get(condition.field.slug)
            if field and self._normalize_data(field.data) not in values:
                return False
        return True

    def _validate_actions(self, rule):
        success = True
        for action in rule.actions.all():
            field = self._fields.get(action.field.slug)
            if not field:
                return success
            if action.is_required:
                field.validators.insert(0, DataRequired())
                success = field.validate(self, [DataRequired()]) and success

            if action.disable_form:
                success = False

                def _disable_form(form, field):
                    raise ValidationError('Registration form is disabled')

                field.validate(self, [_disable_form])
        return success

    def validate(self, **kwargs):
        success = super(_RulesMixin, self).validate(**kwargs)
        if not success:
            return success
        for rule in self.rules:
            conditions_validated = self._validate_conditions(rule)
            if conditions_validated and not self._validate_actions(rule):
                return False
        return success


class _RulesMeta(DefaultMeta):

    def render_field(self, field, render_kw):
        actions = Action.query.filter(
            and_(
                Action.field.has(slug=field.name),
                Action.rule.has(meeting=g.meeting),
                Action.rule.has(rule_type=g.rule_type)
            ))

        context = {}
        if any([a.is_visible for a in actions]):
            context['data-visible'] = 'true'
        if any([a.disable_form for a in actions]):
            context['data-disable-form'] = 'true'

        rules = []
        for action in actions:
            conditions = Condition.query.filter_by(rule=action.rule).all()
            if conditions:
                data = {}
                for c in conditions:
                    data[c.field.slug] = [i.value for i in c.values.all()]
                rules.append(data)
        if rules:
            context['data-rules'] = json.dumps(rules)
            render_kw.update(context)
        return field.widget(field, **render_kw)


class BaseParticipantForm(BaseForm):

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

    def crop_image(self, field_slug, field_value):
        # XXX We need to check if the ratio is respected, and enforce it
        #  here.
        x1 = int(float(getattr(self, '%s_x1_' % field_slug, 0).data))
        y1 = int(float(getattr(self, '%s_y1_' % field_slug, 0).data))
        x2 = int(float(getattr(self, '%s_x2_' % field_slug, 0).data))
        y2 = int(float(getattr(self, '%s_y2_' % field_slug, 0).data))

        unlink_uploaded_file(field_value, 'crop',
                             dir_name=app.config['PATH_CUSTOM_KEY'])
        unlink_thumbnail_file(field_value, dir_name='crops')

        valid_crop = x2 > 0 and y2 > 0
        if valid_crop:
            crop_file(field_value, 'custom', (x1, y1, x2, y2))

    def save(self, participant=None, commit=True):
        participant = participant or Participant()
        participant.meeting_id = g.meeting.id

        if participant.id is None:
            participant.participant_type = self.CUSTOM_FIELDS_TYPE
            db.session.add(participant)

        saveable_added_custom_fields = []
        for field_name, field in self._fields.items():
            if field_name.endswith('_'):
                continue

            cf = self._custom_fields[field.name]
            if cf.is_primary:
                setattr(participant, field_name, field.data)
            elif field.data is not None:
                saveable_added_custom_fields.append(field)

        for field in saveable_added_custom_fields:
            cf = self._custom_fields[field.name]

            field_value = field.save(cf, participant)
            if field.type == "RegistrationImageField" and field_value:
                self.crop_image(field.id, field_value.value)

        db.session.flush()
        participant.set_representing()

        if commit:
            db.session.commit()

        return participant


class ParticipantEditForm(_RulesMixin, BaseParticipantForm):

    Meta = _RulesMeta

    CUSTOM_FIELDS_TYPE = 'participant'


class MediaParticipantEditForm(_RulesMixin, BaseParticipantForm):

    Meta = _RulesMeta

    CUSTOM_FIELDS_TYPE = 'media'


class ParticipantEditFormWithoutRules(BaseParticipantForm):

    CUSTOM_FIELDS_TYPE = 'participant'


class MediaParticipantEditFormWithoutRules(_RulesMixin, BaseParticipantForm):

    Meta = _RulesMeta

    CUSTOM_FIELDS_TYPE = 'media'


class BadgeCategories(BaseForm):

    categories = fields.SelectMultipleField()
    flag = fields.SelectField()

    def __init__(self, *args, **kwargs):
        super(BadgeCategories, self).__init__(*args, **kwargs)
        categories = Category.query.filter_by(
            meeting=g.meeting,
            category_type=Category.PARTICIPANT)
        self.categories.choices = [(c.id, c.title) for c in categories]
        flags = g.meeting.custom_fields.filter_by(
            field_type=CustomField.CHECKBOX,
            is_primary=True)
        self.flag.choices = [('', '---')] + [(f.slug, f.label) for f in flags]


class PrintoutForm(BadgeCategories):

    printout_type = fields.SelectField('Type', choices=PRINTOUT_TYPES)


class FlagForm(BaseForm):

    flag = fields.SelectField()

    def __init__(self, *args, **kwargs):
        custom_field_type = kwargs.pop(
            'custom_field_type', Participant.PARTICIPANT)
        super(FlagForm, self).__init__(*args, **kwargs)
        flags = g.meeting.custom_fields.filter_by(
            field_type=CustomField.CHECKBOX,
            is_primary=True,
            custom_field_type=custom_field_type)
        self.flag.choices = [('', '---')] + [(f.slug, f.label) for f in flags]


class EventsForm(BaseForm):

    events = fields.SelectMultipleField()

    def __init__(self, *args, **kwargs):
        super(EventsForm, self).__init__(*args, **kwargs)
        events = g.meeting.custom_fields.filter_by(
            field_type=CustomField.EVENT)
        self.events.choices = [(e.id, e.label) for e in events]


class CategoryTagForm(BaseForm):

    category_tags = fields.SelectMultipleField()

    def __init__(self, *args, **kwargs):
        super(CategoryTagForm, self).__init__(*args, **kwargs)
        category_tags_query = CategoryTag.query.order_by(CategoryTag.label)
        self.category_tags.choices = [
            (tag.id, tag.label) for tag in category_tags_query]


class ParticipantCategoriesForm(BaseForm):

    categories = fields.SelectMultipleField()
    flag = fields.SelectField()

    def __init__(self, *args, **kwargs):
        super(ParticipantCategoriesForm, self).__init__(*args, **kwargs)
        categories = (Category.query.filter_by(
                      meeting=g.meeting, category_type=Category.PARTICIPANT)
                      .order_by(Category.sort))
        self.categories.choices = [(c.id, c.title) for c in categories]


class MediaCategoriesForm(BaseForm):

    categories = fields.SelectMultipleField()
    flag = fields.SelectField()

    def __init__(self, *args, **kwargs):
        super(MediaCategoriesForm, self).__init__(*args, **kwargs)
        categories = Category.query.filter_by(
            meeting=g.meeting,
            category_type=Category.MEDIA)
        self.categories.choices = [(c.id, c.title) for c in categories]
