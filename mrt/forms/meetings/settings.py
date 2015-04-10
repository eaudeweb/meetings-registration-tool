from flask import g, request

from sqlalchemy import desc
from sqlalchemy.orm.exc import NoResultFound

from wtforms import fields
from wtforms.validators import DataRequired, ValidationError, Length
from wtforms_alchemy import ModelFormField

from mrt.models import CategoryDefault, Category
from mrt.models import CustomField, CustomFieldChoice, CustomFieldValue
from mrt.models import db
from mrt.models import RoleUser, Role, Staff, User
from mrt.models import Translation, UserNotification
from mrt.models import Rule, Condition, ConditionValue, Action

from mrt.definitions import NOTIFICATION_TYPES, NOTIFY_PARTICIPANT
from mrt.utils import copy_attributes, duplicate_uploaded_file
from mrt.utils import get_all_countries

from mrt.forms.base import BaseForm, CustomFieldLabelInputForm
from mrt.forms.fields import SelectMultipleFieldWithoutValidation


class MeetingCategoryAddForm(BaseForm):

    categories = fields.SelectMultipleField(validators=[DataRequired()],
                                            coerce=int, choices=[])

    def __init__(self, *args, **kwargs):
        super(MeetingCategoryAddForm, self).__init__(*args, **kwargs)

        # exclude default categories that have the same name with
        # the categories for the current meeting
        subquery = (
            Category.query.join(Translation)
            .with_entities(Translation.english)
            .filter(Category.meeting == g.meeting)
            .subquery()
        )
        query = (
            CategoryDefault.query
            .filter(
                CategoryDefault.title.has(
                    Translation.english.notin_(subquery)))
            .all()
        )
        self.categories.choices = [(c.id, c.title) for c in query]

    def save(self):
        categories_default = CategoryDefault.query.filter(
            CategoryDefault.id.in_(self.categories.data))
        for category_default in categories_default:
            category = copy_attributes(Category(), category_default,
                                       exclude=('background', ))
            translation = Translation(english=category_default.title.english)
            db.session.add(translation)
            db.session.flush()
            category.title = translation
            category.meeting = g.meeting
            filename = duplicate_uploaded_file(category_default.background,
                                               'backgrounds')
            if filename:
                category.background = filename.basename()
            db.session.add(category)
        db.session.commit()


class CustomFieldEditForm(BaseForm):

    label = ModelFormField(CustomFieldLabelInputForm, label='Field label')
    custom_field_choices = SelectMultipleFieldWithoutValidation(
        'Choices', choices=[], coerce=unicode)

    class Meta:
        model = CustomField

    def __init__(self, *args, **kwargs):
        custom_field_type = kwargs.pop('custom_field_type', None)
        super(CustomFieldEditForm, self).__init__(*args, **kwargs)

        excluded_types = [CustomField.SELECT, CustomField.CATEGORY,
                          CustomField.LANGUAGE]
        if custom_field_type == CustomField.MEDIA:
            excluded_types.append(CustomField.EVENT)
        self.field_type.choices = [i for i in self.field_type.choices
                                   if i[0] not in excluded_types]

        if custom_field_type:
            self.custom_field_type.data = custom_field_type
            setattr(self.label.form, 'custom_field_type', custom_field_type)

        if self.field_type.data == CustomField.EVENT:
            self.required.data = False

        if self.field_type.data == CustomField.MULTI_CHECKBOX and self.obj:
            self.custom_field_choices.choices = (
                CustomFieldChoice.query.filter_by(custom_field=self.obj)
                .join(Translation)
                .with_entities(Translation.english, Translation.english)
            )
            count = CustomFieldValue.query.filter_by(
                custom_field=self.obj).count()
            if count:
                self.custom_field_choices.flags.disabled = True
            if request.method == 'GET':
                self.custom_field_choices.data = [
                    i[0] for i in self.custom_field_choices.choices]

    def save(self):
        cf = self.obj or CustomField()
        self.populate_obj(cf)
        cf.meeting = g.meeting

        is_choice_field_disabled = self.custom_field_choices.flags.disabled
        if (cf.field_type == CustomField.MULTI_CHECKBOX
           and not is_choice_field_disabled):
            CustomFieldChoice.query.filter_by(custom_field=cf).delete()
            for choice in self.custom_field_choices.data:
                cf_choice = CustomFieldChoice(custom_field=cf)
                cf_choice.value = Translation(english=choice)
                db.session.add(cf_choice)

        if not cf.id:
            last_sort = (
                CustomField.query.filter_by(meeting=g.meeting)
                .with_entities(CustomField.sort)
                .order_by(desc(CustomField.sort))
                .first())
            if last_sort:
                cf.sort = last_sort[0] + 1
            db.session.add(cf)
        db.session.commit()


class RoleUserEditForm(BaseForm):

    class Meta:
        model = RoleUser

    user_id = fields.SelectField('User',
                                 validators=[DataRequired()],
                                 coerce=int)
    role_id = fields.SelectField('Role',
                                 validators=[DataRequired()],
                                 coerce=int)

    def validate_user_id(self, field):
        obj = RoleUser.query.filter_by(user_id=field.data,
                                       meeting_id=g.meeting.id,
                                       role_id=self.role_id.data).first()
        if obj and obj != self.obj:
            raise ValidationError('Role already exists')

    def __init__(self, *args, **kwargs):
        if kwargs['obj']:
            kwargs.setdefault('user_id', kwargs['obj'].user.id)
            kwargs.setdefault('role_id', kwargs['obj'].role.id)
        super(RoleUserEditForm, self).__init__(*args, **kwargs)
        self.user_id.choices = [(
            x.user.id, x.user.email) for x in Staff.query.all()]
        self.role_id.choices = [(x.id, x.name) for x in Role.query.all()]

    def save(self):
        user_role = self.obj or self.meta.model()
        with db.session.no_autoflush:
            user_role.user = User.query.get_or_404(self.user_id.data)
            user_role.role = Role.query.get_or_404(self.role_id.data)
        user_role.meeting = g.meeting
        if user_role.id is None:
            db.session.add(user_role)
        db.session.commit()


class UserNotificationForm(BaseForm):

    class Meta:
        model = UserNotification

    user_id = fields.SelectField('Staff', validators=[DataRequired()],
                                 coerce=int)
    notification_type = fields.SelectField(
        'Type',
        validators=[DataRequired()],
        choices=NOTIFICATION_TYPES)

    def __init__(self, *args, **kwargs):
        super(UserNotificationForm, self).__init__(*args, **kwargs)
        staff = RoleUser.query.filter_by(meeting=g.meeting).all()
        self.user_id.choices = [(x.user.id, x.user.email) for x in staff]
        if not g.meeting.media_participant_enabled:
            self.notification_type.choices = (NOTIFY_PARTICIPANT,)

    def validate_notification_type(self, field):
        obj = UserNotification.query.filter_by(notification_type=field.data,
                                               user_id=self.user_id.data,
                                               meeting_id=g.meeting.id).first()
        if obj and obj != self.obj:
            raise ValidationError('Subscriber already exists')

    def save(self):
        user_notification = self.obj or self.meta.model()
        self.populate_obj(user_notification)
        if user_notification.id is None:
            user_notification.meeting = g.meeting
            db.session.add(user_notification)
        db.session.commit()


class ConditionForm(BaseForm):

    CHECKBOX_VALUES = [('true', 'True'), ('false', 'False')]

    field = fields.SelectField('Field', coerce=int)
    values = fields.SelectMultipleField('Values', [DataRequired()], choices=[])

    def __init__(self, *args, **kwargs):
        super(ConditionForm, self).__init__(*args, **kwargs)
        query = (
            CustomField.query.filter_by(meeting_id=g.meeting.id)
            .filter_by(custom_field_type=CustomField.PARTICIPANT)
            .filter(CustomField.field_type.in_(
                [CustomField.CATEGORY, CustomField.COUNTRY,
                 CustomField.CHECKBOX, CustomField.SELECT]))
            .filter_by(visible_on_registration_form=True)
            .order_by(CustomField.sort))
        self.field.choices = [(c.id, c) for c in query]

        self.cf = None
        if self.field.data:
            self.cf = (
                CustomField.query
                .filter_by(id=int(self.field.data), meeting=g.meeting)
                .one()
            )
            dispatch = {
                CustomField.CATEGORY: self._get_query_for_category,
                CustomField.COUNTRY: self._get_query_for_countries,
                CustomField.CHECKBOX: self._get_query_for_checkbox,
                CustomField.SELECT: self._get_query_for_select,
            }
            self.values.choices = dispatch[self.cf.field_type.code]()

    def _get_query_for_category(self):
        query = Category.get_categories_for_meeting(Category.PARTICIPANT)
        return [(str(c.id), unicode(c)) for c in query]

    def _get_query_for_countries(self):
        return get_all_countries()

    def _get_query_for_checkbox(self):
        return self.CHECKBOX_VALUES

    def _get_query_for_select(self):
        return [(unicode(i), unicode(i)) for i in self.cf.choices.all()]

    def save(self, rule):
        condition = Condition(rule=rule, field=self.cf)
        db.session.add(condition)
        db.session.flush()
        for value in self.values.data:
            condition_value = ConditionValue(condition=condition,
                                             value=value)
            db.session.add(condition_value)


class ActionForm(BaseForm):

    field = fields.SelectField('Field', coerce=int)
    is_required = fields.BooleanField('Required')
    is_visible = fields.BooleanField('Visible')

    def __init__(self, *args, **kwargs):
        super(ActionForm, self).__init__(*args, **kwargs)
        query = (
            CustomField.query.filter_by(meeting_id=g.meeting.id)
            .filter_by(custom_field_type=CustomField.PARTICIPANT)
            .for_registration()
            .order_by(CustomField.sort))
        self.field.choices = [(c.id, c) for c in query]
        self.cf = None
        if self.field.data:
            self.cf = (
                CustomField.query
                .filter_by(id=self.field.data, meeting=g.meeting)
                .one())

    def save(self, rule):
        action = Action(rule=rule, field=self.cf)
        action.is_required = self.is_required.data
        action.is_visible = self.is_visible.data
        db.session.add(action)


class RuleForm(BaseForm):

    name = fields.StringField('Rule name', [DataRequired(), Length(max=64)])
    conditions = fields.FieldList(fields.FormField(ConditionForm),
                                  min_entries=1)
    actions = fields.FieldList(fields.FormField(ActionForm),
                               min_entries=1)

    def __init__(self, *args, **kwargs):
        self.rule = rule = kwargs.pop('rule', None)
        formdata = args[0] if args else None
        super(RuleForm, self).__init__(*args, **kwargs)
        if rule:
            self.name.process(formdata, rule.name)

    def validate_name(self, field):
        if self.rule and (field.data == self.rule.name):
            return
        try:
            Rule.query.filter_by(name=field.data, meeting=g.meeting).one()
            raise ValidationError('Name must be unique')
        except NoResultFound:
            pass

    def validate_actions(self, field):
        condition_fields = set([i['field'] for i in self.conditions.data])
        action_fields = set([i['field'] for i in self.actions.data])
        if condition_fields & action_fields:
            raise ValidationError('Action fields should be different '
                                  'from condition fields')
        if len(action_fields) != len(self.actions.data):
            raise ValidationError('Actions fields should be different')

    def save(self):
        rule = self.rule or Rule(meeting=g.meeting)
        rule.name = self.name.data
        # if edit, delete all conditions and actions for this rule and their
        # corresponding values
        if rule.id:
            Condition.query.filter_by(rule=rule).delete()
            Action.query.filter_by(rule=rule).delete()
        for condition_form in self.conditions:
            condition_form.save(rule)
        for action_form in self.actions:
            action_form.save(rule)
        if not rule.id:
            db.session.add(rule)
        db.session.commit()
