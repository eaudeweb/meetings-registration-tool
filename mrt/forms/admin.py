from wtforms_alchemy import ModelFormField

from .base import BaseForm
from mrt.models import Staff, db
from mrt.forms.auth import UserForm


class StaffAddForm(BaseForm):

    class Meta:
        model = Staff

    user = ModelFormField(UserForm, label='User')

    def save(self):
        staff = Staff()

        self.populate_obj(staff)
        staff.user.set_password(staff.user.password)

        db.session.add(staff)
        db.session.commit()


class StaffEditForm(BaseForm):

    class Meta:
        model = Staff

    def save(self):
        self.populate_obj(self.obj)

        db.session.add(self.obj)
        db.session.commit()
