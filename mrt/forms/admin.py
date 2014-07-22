from datetime import datetime
from uuid import uuid4

from flaskext.uploads import UploadSet, IMAGES
from flask_wtf.file import FileField, FileAllowed
from sqlalchemy.orm.exc import NoResultFound
from wtforms_alchemy import ModelFormField

from mrt.mail import send_activation_mail
from mrt.models import db
from mrt.models import Staff, User, CategoryDefault
from .base import BaseForm, TranslationInpuForm


backgrounds = UploadSet('backgrounds', IMAGES)


def _staff_user_unique(*args, **kwargs):
    def validate(form, field):
        return Staff.query.filter(Staff.user.has(email=field.data)).first()
    return validate


class UserForm(BaseForm):

    class Meta:
        model = User
        only = ('email',)
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
                                  is_active=False)

            if not staff.user.is_active:
                send_activation_mail(
                    staff.user.email, staff.user.recover_token)

        if staff.id is None:
            db.session.add(staff)
        db.session.commit()
        return staff


class CategoryEditForm(BaseForm):

    class Meta:
        model = CategoryDefault

    name = ModelFormField(TranslationInpuForm, label='Name')
    background = FileField('Background',
                           [FileAllowed(backgrounds, 'Image is not valid')])

    def save(self):
        category = self.obj or CategoryDefault()
        self.populate_obj(category)
        if self.background.data:
            category.background = backgrounds.save(self.background.data)
        else:
            category.background = None
        if category.id is None:
            db.session.add(category)
        db.session.commit()
        return category
