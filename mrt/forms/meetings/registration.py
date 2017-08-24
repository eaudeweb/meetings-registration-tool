import time
from base64 import b64encode, b64decode
from uuid import uuid4

from flask import current_app as app
from flask_babel import gettext as _
from flask_babel import lazy_gettext as __
from flask_wtf.file import FileAllowed
from flask_uploads import IMAGES, DOCUMENTS

from wtforms import Form, StringField, PasswordField, validators
from wtforms import HiddenField

from mrt.forms.meetings import BaseParticipantForm
from mrt.forms.meetings.participant import _RulesMixin, _RulesMeta
from mrt.forms.fields import RegistrationImageField, RegistrationDocumentField
from mrt.models import db, User, CustomField
from mrt import utils


class RegistrationForm(_RulesMixin, BaseParticipantForm):

    Meta = _RulesMeta

    # prevent robots from abusing
    TIME_LIMIT = 2  # seconds

    CUSTOM_FIELDS_TYPE = 'participant'

    _CUSTOM_FIELDS_MAP = {
        CustomField.IMAGE: {
            'field': RegistrationImageField,
            'validators': [FileAllowed(IMAGES)]
        },
        CustomField.DOCUMENT: {
            'field': RegistrationDocumentField,
            'validators': [FileAllowed(DOCUMENTS + ('pdf',))]
        },
    }

    ts_ = HiddenField(validators=[validators.DataRequired()])

    def __init__(self, *args, **kwargs):
        super(RegistrationForm, self).__init__(*args, **kwargs)
        if not self.ts_.data:
            ts = int(time.time())
            self.ts_.process_data(b64encode(str(ts)))

    def validate_ts_(self, field):
        # skip validation on debug
        if not app.config.get('DEBUG', False):
            current_time = int(time.time())

            try:
                ts = int(b64decode(self.data['ts_']))
            except (ValueError, TypeError):
                raise validators.ValidationError('Runtime error.')
            if current_time - ts <= self.TIME_LIMIT:
                raise validators.ValidationError('Runtime error.')

    def save(self):
        participant = super(RegistrationForm, self).save(commit=False)
        participant.registration_token = str(uuid4())
        db.session.commit()
        return participant


class MediaRegistrationForm(RegistrationForm):

    CUSTOM_FIELDS_TYPE = 'media'


class RegistrationUserForm(Form):

    email = StringField(__('Email'), [validators.Email()])
    password = PasswordField(__('Password'), [validators.DataRequired()])
    confirm = PasswordField(
        __('Confirm Password'), [validators.DataRequired()])

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
