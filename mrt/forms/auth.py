from uuid import uuid4
from datetime import datetime

from flask.ext.login import current_user

from wtforms import Form
from wtforms import StringField, PasswordField, validators

from mrt.models import db, User, Staff
from .base import BaseForm


class LoginForm(Form):

    email = StringField('Email', [validators.Email()])
    password = PasswordField('Password')

    def __init__(self, *args, **kwargs):
        self.staff_only = kwargs.pop('staff_only', False)
        super(LoginForm, self).__init__(*args, **kwargs)

    def validate_email(self, field):
        user = self.get_user()
        if user is None:
            raise validators.ValidationError('Invalid user')
        if not user.is_active():
            raise validators.ValidationError('Inactive user')

    def validate_password(self, field):
        user = self.get_user()
        if (user and user.is_active() and
           not user.check_password(self.password.data)):
            raise validators.ValidationError('Invalid password')

    def get_user(self):
        query = User.query.filter_by(email=self.email.data)
        if self.staff_only:
            query = query.join(Staff)
        return query.scalar()


class UserForm(BaseForm):

    class Meta:
        model = User


class RecoverForm(Form):

    email = StringField('Email', [validators.Email()])

    def validate_email(self, field):
        user = self.get_user()
        if user is None:
            raise validators.ValidationError('Invalid user')

    def get_user(self):
        return User.query.filter_by(email=self.email.data).first()

    def save(self):
        user = self.get_user()
        token = str(uuid4())
        time = datetime.now()

        user.recover_token = token
        user.recover_time = time
        db.session.commit()

        return user


class ResetPasswordForm(Form):

    password = PasswordField('Password', [validators.DataRequired()])
    confirm = PasswordField('Confirm Password', [validators.DataRequired()])

    def validate_confirm(self, field):
        if self.password.data != self.confirm.data:
            raise validators.ValidationError('Passwords differ!')


class AdminChangePasswordForm(Form):
    new_password = PasswordField('New Password', [validators.DataRequired()])
    confirm = PasswordField('Confirm Password', [validators.DataRequired()])

    def __init__(self, *args, **kwargs):
        super(AdminChangePasswordForm, self).__init__(*args, **kwargs)
        self.user = kwargs.get('user', current_user)

    def validate_confirm(self, field):
        if self.new_password.data != self.confirm.data:
            raise validators.ValidationError('Passwords differ')

    def save(self):
        self.user.set_password(self.new_password.data)
        db.session.commit()


class ChangePasswordForm(AdminChangePasswordForm):
    password = PasswordField('Password', [validators.DataRequired()])

    def validate_password(self, field):
        if not self.user.check_password(self.password.data):
            raise validators.ValidationError('Password is incorrect')
