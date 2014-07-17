from wtforms import Form
from wtforms import TextField, PasswordField, validators

from .base import BaseForm
from mrt.models import User


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
