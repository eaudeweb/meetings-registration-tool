from datetime import datetime
from uuid import uuid4

from flask.ext.login import current_user
from flask.ext.uploads import UploadSet, IMAGES
from flask_wtf.file import FileField, FileAllowed

from sqlalchemy import desc
from sqlalchemy.orm.exc import NoResultFound
from wtforms import ValidationError, BooleanField, fields
from wtforms.validators import DataRequired
from wtforms_alchemy import ModelFormField
from wtforms.ext.sqlalchemy.fields import QuerySelectField

from mrt.mail import send_activation_mail
from mrt.models import db
from mrt.models import Staff, User, Role
from mrt.models import CategoryDefault, Category, CategoryClass
from mrt.models import PhraseDefault, Phrase
from mrt.models import MeetingType, CustomField
from mrt.utils import unlink_uploaded_file
from mrt.definitions import PERMISSIONS
from mrt.forms.meetings import CustomFieldEditForm

from .base import BaseForm, DescriptionInputForm
from .base import AdminCustomFieldLabelInputForm
from .base import DefaultCategoryTitleInputForm, CategoryTitleInputForm
from .fields import slug_unique


backgrounds = UploadSet('backgrounds', IMAGES)


def _staff_user_unique(*args, **kwargs):
    def validate(form, field):
        if form.obj and form.obj.email == field.data:
            return True
        try:
            Staff.query.filter(Staff.user.has(email=field.data)).one()
            raise ValidationError(
                'Another staff with this email already exists')
        except NoResultFound:
            pass
    return validate


class UserForm(BaseForm):

    class Meta:
        model = User
        only = ('email', 'is_superuser')
        unique_validator = _staff_user_unique

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        if not current_user.is_superuser or current_user == self.obj:
            del self._fields['is_superuser']
            del self.is_superuser


class UserSearchForm(BaseForm):

    search = fields.StringField('Search')


class StaffEditForm(BaseForm):

    class Meta:
        model = Staff

    user = ModelFormField(UserForm)

    def save(self):
        staff = self.obj or Staff()
        # do not use populate_obj here, session.add will not work
        staff.full_name = self.full_name.data
        staff.title = self.title.data
        email = self.user.email.data

        if staff.user is None:
            try:
                staff.user = User.query.filter_by(email=email).one()
            except NoResultFound:
                staff.user = User(email=email,
                                  recover_token=str(uuid4()),
                                  recover_time=datetime.now())
                send_activation_mail(staff.user.email,
                                     staff.user.recover_token)
        else:
            staff.user.email = email

        if self.user.is_superuser:
            staff.user.is_superuser = self.user.is_superuser.data

        if staff.id is None:
            db.session.add(staff)
        db.session.commit()
        return staff


class CategoryEditBaseForm(BaseForm):

    background = FileField('Background',
                           [FileAllowed(backgrounds, 'Image is not valid')])
    background_delete = BooleanField()
    category_class = QuerySelectField(get_label='label', allow_blank=True, blank_text=u'No class')

    def __init__(self, *args, **kwargs):
        super(CategoryEditBaseForm, self).__init__(*args, **kwargs)
        self.category_class.query = CategoryClass.query.order_by(CategoryClass.label)

    def save(self):
        category = self.obj or self.meta.model()
        background = category.background
        self.populate_obj(category)
        category.background = background

        if self.background.data:
            unlink_uploaded_file(background, 'backgrounds')
            category.background = backgrounds.save(
                self.background.data,
                name=str(uuid4()) + '.')
        elif self.background_delete.data:
            unlink_uploaded_file(background, 'backgrounds')
            category.background = None

        if category.id is None:
            db.session.add(category)
        db.session.commit()

        return category


class CategoryDefaultEditForm(CategoryEditBaseForm):

    title = ModelFormField(DefaultCategoryTitleInputForm, label='Title')
    meeting_type_slugs = fields.SelectMultipleField('Meeting types')

    def __init__(self, *args, **kwargs):
        super(CategoryDefaultEditForm, self).__init__(*args, **kwargs)
        self.meeting_type_slugs.choices = [
            (m.slug, m.label) for m in MeetingType.query.ignore_def()]
        if self.obj and self.meeting_type_slugs.data is None:
            self.meeting_type_slugs.data = [
                m.slug for m in self.obj.meeting_types]

    class Meta:
        model = CategoryDefault

    def save(self):
        category = super(CategoryDefaultEditForm, self).save()
        category.meeting_types = MeetingType.query.filter(
            MeetingType.slug.in_(self.meeting_type_slugs.data)).all()

        db.session.commit()
        return category


class CategoryEditForm(CategoryEditBaseForm):

    title = ModelFormField(CategoryTitleInputForm, label='Title')

    class Meta:
        model = Category


class CategoryClassEditForm(BaseForm):

    class Meta:
        model = CategoryClass
        only = ('label',)

    def __init__(self, *args, **kwargs):
        super(CategoryClassEditForm, self).__init__(*args, **kwargs)

    def save(self):
        category_class = self.obj or self.meta.model()
        self.populate_obj(category_class)
        db.session.add(category_class)
        db.session.commit()

        return category_class


class PhraseEditBaseForm(BaseForm):

    description = ModelFormField(DescriptionInputForm, label='Description')

    def save(self):
        phrase = self.obj or self.meta.model()
        self.populate_obj(phrase)
        if phrase.id is None:
            db.session.add(phrase)
        db.session.commit()


class PhraseDefaultEditForm(PhraseEditBaseForm):

    class Meta:
        model = PhraseDefault
        exclude = ('name', 'group', 'sort')


class PhraseEditForm(PhraseEditBaseForm):

    class Meta:
        model = Phrase
        exclude = ('name', 'group', 'sort')


class RoleEditForm(BaseForm):

    class Meta:
        model = Role

    permissions = fields.SelectMultipleField('Permissions',
                                             validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        super(RoleEditForm, self).__init__(*args, **kwargs)
        self.permissions.choices = PERMISSIONS

    def save(self):
        role = self.obj or self.meta.model()
        self.populate_obj(role)
        if role.id is None:
            db.session.add(role)
        db.session.commit()


class MeetingTypeEditForm(BaseForm):

    class Meta:
        model = MeetingType
        only = ('slug', 'label')
        field_args = {
            'slug': {'validators': [slug_unique]}
        }

    def __init__(self, *args, **kwargs):
        super(MeetingTypeEditForm, self).__init__(*args, **kwargs)
        if self.obj:
            del self._fields['slug']

    def save(self):
        meeting_type = self.obj or MeetingType()
        self.populate_obj(meeting_type)
        db.session.add(meeting_type)
        if not meeting_type.default_phrases:
            meeting_type.load_default_phrases()
        db.session.commit()


class AdminCustomFieldEditForm(CustomFieldEditForm):

    label = ModelFormField(AdminCustomFieldLabelInputForm, label='Field label')
    meeting_type_slugs = fields.SelectMultipleField('Meeting types')

    def __init__(self, *args, **kwargs):
        super(AdminCustomFieldEditForm, self).__init__(*args, **kwargs)
        self.meeting_type_slugs.choices = [
            (m.slug, m.label) for m in MeetingType.query.ignore_def()]
        if self.obj and self.meeting_type_slugs.data is None:
            self.meeting_type_slugs.data = [
                m.slug for m in self.obj.meeting_types]

    def save(self):
        custom_field = self.obj or CustomField()
        self.populate_obj(custom_field)
        custom_field.meeting_types = MeetingType.query.filter(
            MeetingType.slug.in_(self.meeting_type_slugs.data)).all()

        db.session.commit()
        if not custom_field.id:
            last_sort = (
                CustomField.query.with_entities(CustomField.sort)
                .order_by(desc(CustomField.sort))
                .first())
            if last_sort:
                custom_field.sort = last_sort[0] + 1
            db.session.add(custom_field)
        db.session.commit()
