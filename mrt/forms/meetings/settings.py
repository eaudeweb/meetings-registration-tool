from uuid import uuid4

from flask import g
from werkzeug import FileStorage, OrderedMultiDict

from flask.ext.uploads import UploadSet, IMAGES, TEXT, DOCUMENTS
from flask_wtf.file import FileField, FileAllowed

from wtforms import fields
from wtforms.validators import DataRequired, ValidationError
from wtforms_alchemy import ModelFormField

from mrt.models import db
from mrt.models import CategoryDefault, Category
from mrt.models import RoleUser, Role, Staff, User
from mrt.models import CustomField, CustomFieldValue
from mrt.models import Translation, UserNotification
from mrt.utils import copy_model_fields, duplicate_uploaded_file
from mrt.utils import unlink_participant_photo
from mrt.definitions import NOTIFICATION_TYPES

from mrt.forms.base import BaseForm, TranslationInpuForm
from mrt.forms.base import BooleanField


custom_upload = UploadSet('custom', TEXT + DOCUMENTS + IMAGES)


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
            category = copy_model_fields(
                Category, category_default,
                exclude=('id', 'title_id', 'background'))
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

    label = ModelFormField(TranslationInpuForm, label='Field label')

    class Meta:
        model = CustomField

    def save(self):
        custom_field = self.obj or CustomField()
        self.populate_obj(custom_field)
        custom_field.meeting = g.meeting
        if not custom_field.slug:
            db.session.add(custom_field)
        db.session.commit()


class CustomFieldMagicForm(BaseForm):

    MAP = {
        'text': {'field': fields.StringField},
        'checkbox': {'field': BooleanField},
        'image': {'field': FileField, 'validators': [FileAllowed(IMAGES)]}
    }

    def save(self, participant=None):
        participant = self._participant or participant
        items = []
        for field_name, field in self._fields.items():
            custom_field_value = (
                CustomFieldValue.query
                .filter(CustomFieldValue.custom_field.has(slug=field_name))
                .filter(CustomFieldValue.participant == participant)
                .scalar())
            custom_field_value = custom_field_value or CustomFieldValue()
            if isinstance(field.data, FileStorage):
                current_filename = custom_field_value.value
                custom_field_value.value = custom_upload.save(
                    field.data, name=str(uuid4()) + '.')
                unlink_participant_photo(current_filename)
            else:
                custom_field_value.value = field.data
            custom_field_value.custom_field = self._custom_fields[field_name]
            custom_field_value.participant = participant
            if not custom_field_value.id:
                db.session.add(custom_field_value)
            items.append(custom_field_value)
        db.session.commit()
        return items


class CustomFieldMagic(object):
    pass


def custom_object_factory(participant, field_type=None, obj=CustomFieldMagic):
    object_attrs = {}
    custom_field_values = CustomFieldValue.query.filter_by(
        participant=participant)
    if field_type:
        custom_field_values = custom_field_values.filter(
            CustomFieldValue.custom_field.has(field_type=field_type))
    for val in custom_field_values:
        object_attrs[val.custom_field.slug] = str(val.value)
    return type(obj)(obj.__name__, (obj,), object_attrs)


def custom_form_factory(participant, slug=None, field_type=None,
                        form=CustomFieldMagicForm):
    custom_fields = CustomField.query.filter_by(meeting_id=g.meeting.id)
    custom_fields = custom_fields.order_by(CustomField.sort)
    if field_type:
        custom_fields = custom_fields.filter_by(field_type=field_type)

    if slug:
        custom_fields = [custom_fields.filter_by(slug=slug).first_or_404()]

    custom_fields_dict = OrderedMultiDict({c.slug: c for c in custom_fields})
    form_attrs = {
        '_custom_fields': custom_fields_dict,
        '_participant': participant,
    }
    for f in custom_fields:
        field_attrs = {'label': f.label, 'validators': []}
        if f.required:
            field_attrs['validators'].append(DataRequired())
        validators = form.MAP[f.field_type.code].get('validators', [])
        for validator in validators:
            field_attrs['validators'].append(validator)

        FormField = form.MAP[f.field_type.code]['field']
        form_attrs[f.slug] = FormField(**field_attrs)

    return type(form)(form.__name__, (form,), form_attrs)


class RoleUserEditForm(BaseForm):

    class Meta:
        model = RoleUser

    user_id = fields.SelectField('User',
                                 validators=[DataRequired()],
                                 coerce=int)
    role_id = fields.SelectField('Role',
                                 validators=[DataRequired()],
                                 coerce=int)

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
        user_role.user = User.query.get_or_404(self.user_id.data)
        user_role.role = Role.query.get_or_404(self.role_id.data)
        user_role.meeting = g.meeting
        if user_role.id is None:
            db.session.add(user_role)
        db.session.commit()


class UserNotificationForm(BaseForm):

    class Meta:
        model = UserNotification

    user_id = fields.SelectField('Staff',
                                 validators=[DataRequired()],
                                 coerce=int)
    notification_type = fields.SelectField('Type',
                                           validators=[DataRequired()],
                                           choices=NOTIFICATION_TYPES)

    def __init__(self, *args, **kwargs):
        super(UserNotificationForm, self).__init__(*args, **kwargs)
        staff = RoleUser.query.filter_by(meeting=g.meeting).all()
        self.user_id.choices = [(x.user.id, x.user.email) for x in staff]

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
