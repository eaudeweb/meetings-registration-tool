from wtforms_alchemy import ModelFormField
from sqlalchemy.orm.exc import NoResultFound
from uuid import uuid4
from datetime import datetime

from .base import BaseForm
from mrt.models import db, Staff, User
from mrt.mail import send_activation_mail


def _staff_user_unique(*args, **kwargs):
    def validate(form, field):
        return Staff.query.filter(Staff.user.has(email=field.data)).scalar()
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
        staff.full_name = self.full_name.data
        if staff.user is None:
            try:
                staff.user = User.query.filter_by(
                    email=self.user.email.data).one()
            except NoResultFound:
                staff.user = User(email=self.user.email.data,
                                  recover_token=str(uuid4()),
                                  recover_time=datetime.now(),
                                  is_active=False)
            send_activation_mail(staff.user.email, staff.user.recover_token)

        if staff.id is None:
            db.session.add(staff)
        db.session.commit()
        return staff
