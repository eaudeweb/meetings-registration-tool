from flask.ext.babel import gettext as _
from flask_wtf.file import FileAllowed
from flask.ext.uploads import IMAGES

from wtforms import Form, StringField, PasswordField, validators

from mrt.forms.meetings import ParticipantEditForm
from mrt.forms.base import FileField
from mrt.models import db, User, CustomField
from mrt import utils


class RegistrationForm(ParticipantEditForm):

    _CUSTOM_FIELDS_MAP = {
        CustomField.IMAGE: {
            'field': FileField,
            'validators': [FileAllowed(IMAGES)]
        },
    }


class MediaRegistrationForm(RegistrationForm):

    _CUSTOM_FIELDS_TYPE = 'media'


class RegistrationUserForm(Form):

    email = StringField('Email', [validators.Email()])
    password = PasswordField('Password', [validators.DataRequired()])
    confirm = PasswordField('Confirm Password', [validators.DataRequired()])

    def validate_email(self, field):
        if not utils.validate_email(field.data):
            raise validators.ValidationError(
                _('Invalid email. Enter another email.'))
        user = User.query.filter_by(email=field.data).scalar()
        if user:
            raise validators.ValidationError(
                _('Another participant is already registered with this email '
                  'address.'))

    def validate_confirm(self, field):
        if self.password.data != self.confirm.data:
            raise validators.ValidationError('Passwords differ')

    def save(self):
        user = User(email=self.email.data)
        user.set_password(self.password.data)
        db.session.add(user)
        db.session.commit()
        return user
