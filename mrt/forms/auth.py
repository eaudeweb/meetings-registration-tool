from wtforms import Form
from wtforms import TextField, PasswordField, validators

from uuid import uuid4
from datetime import datetime

from .base import BaseForm
from mrt.models import db, User


class LoginForm(Form):

    email = TextField('Email')
    password = PasswordField('Password')

    def validate_email(self, field):
        user = self.get_user()

        if user is None:
            raise validators.ValidationError('Invalid user')

    def validate_password(self, field):
        user = self.get_user()

        if user and not user.check_password(self.password.data):
            raise validators.ValidationError('Invalid password')

    def get_user(self):
        return User.query.filter_by(email=self.email.data).first()


class UserForm(BaseForm):

    class Meta:
        model = User


class RecoverForm(Form):

    email = TextField('Email', [validators.Required()])

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

        db.session.add(user)
        db.session.commit()
