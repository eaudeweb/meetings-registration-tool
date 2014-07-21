from wtforms import TextField, validators

from uuid import uuid4
from datetime import datetime

from .base import BaseForm
from mrt.models import db, Staff, User
from mrt.mail import send_activation_mail


class StaffEditForm(BaseForm):

    class Meta:
        model = Staff

    email = TextField('Email', [validators.Required()])

    def get_user(self):
        return User.query.filter_by(email=self.email.data).first()

    def save(self):
        staff = self.obj or Staff()
        self.populate_obj(staff)
        staff.user = self.get_user()
        if staff.user is None:
            staff.user = User(email=self.email.data, is_active=False)
            staff.user.recover_token = str(uuid4())
            staff.user.recover_time = datetime.now()
            db.session.add(staff.user)

            send_activation_mail(staff.user.email, staff.user.recover_token)

        if staff.id is None:
            db.session.add(staff)
        db.session.commit()
        return staff
