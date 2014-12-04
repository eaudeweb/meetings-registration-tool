from datetime import datetime
from uuid import uuid4

from flask.ext.uploads import UploadSet, IMAGES
from flask_wtf.file import FileField, FileAllowed

from sqlalchemy.orm.exc import NoResultFound
from wtforms import ValidationError, BooleanField, fields
from wtforms.validators import DataRequired
from wtforms_alchemy import ModelFormField

from mrt.mail import send_activation_mail
from mrt.models import db
from mrt.models import Staff, User, Role
from mrt.models import CategoryDefault, Category
from mrt.models import PhraseDefault, Phrase
from mrt.utils import unlink_uploaded_file
from mrt.definitions import PERMISSIONS

from .base import BaseForm, DescriptionInputForm
from .base import DefaultCategoryTitleInputForm, CategoryTitleInputForm


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
                staff.user = User(email=self.user.email.data,
                                  recover_token=str(uuid4()),
                                  recover_time=datetime.now(),
                                  is_superuser=self.user.is_superuser.data)
                send_activation_mail(staff.user.email,
                                     staff.user.recover_token)
        else:
            staff.user.email = self.user.email.data
            staff.user.is_superuser = self.user.is_superuser.data

        if staff.id is None:
            db.session.add(staff)
        db.session.commit()
        return staff


class CategoryEditBaseForm(BaseForm):

    background = FileField('Background',
                           [FileAllowed(backgrounds, 'Image is not valid')])
    background_delete = BooleanField()

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
        else:
            if self.background_delete.data:
                unlink_uploaded_file(background, 'backgrounds')
                category.background = None

        if category.id is None:
            db.session.add(category)
        db.session.commit()

        return category


class CategoryDefaultEditForm(CategoryEditBaseForm):

    title = ModelFormField(DefaultCategoryTitleInputForm, label='Title')

    class Meta:
        model = CategoryDefault


class CategoryEditForm(CategoryEditBaseForm):

    title = ModelFormField(CategoryTitleInputForm, label='Title')

    class Meta:
        model = Category


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
