from flask import g

from sqlalchemy import desc

from wtforms import fields
from wtforms.validators import DataRequired, ValidationError
from wtforms_alchemy import ModelFormField

from mrt.models import CategoryDefault, Category, CustomField
from mrt.models import db
from mrt.models import RoleUser, Role, Staff, User
from mrt.models import Translation, UserNotification

from mrt.definitions import NOTIFICATION_TYPES
from mrt.utils import copy_model_fields, duplicate_uploaded_file

from mrt.forms.base import BaseForm, TranslationInputForm


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

    label = ModelFormField(TranslationInputForm, label='Field label')

    class Meta:
        model = CustomField

    def save(self):
        custom_field = self.obj or CustomField()
        self.populate_obj(custom_field)
        custom_field.meeting = g.meeting
        if not custom_field.slug:
            last_sort = (
                CustomField.query.with_entities(CustomField.sort)
                .order_by(desc(CustomField.sort))
                .first())
            if last_sort:
                custom_field.sort = last_sort[0] + 1
            db.session.add(custom_field)
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
