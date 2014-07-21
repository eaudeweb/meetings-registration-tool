from flask.ext.sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy_utils import ChoiceType, CountryType

from datetime import datetime


db = SQLAlchemy()


class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=True)
    recover_token = db.Column(db.String(64))
    recover_time = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return '{}'.format(self.email)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def is_authenticated(self):
        return True

    def is_active(self):
        return self.is_active

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)

    def token_is_active(self):
        return (datetime.now() - self.recover_time).seconds < 86400


class Staff(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64), nullable=True, info={'label': 'Ttile'})
    full_name = db.Column(db.String(128), nullable=False,
                          info={'label': 'Full Name'})

    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id'),
        nullable=False)
    user = db.relationship(
        'User',
        backref=db.backref('staffs', lazy='dynamic'))

    role_id = db.Column(
        db.Integer, db.ForeignKey('role.id'),
        nullable=True)
    role = db.relationship(
        'Role',
        backref=db.backref('staffs', lazy='dynamic'))

    def __repr__(self):
        return '{}'.format(self.full_name)


class Role(db.Model):

    id = db.Column(db.Integer, primary_key=True)


class Participant(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    meeting_id = db.Column(
        db.Integer, db.ForeignKey('meeting.id'),
        nullable=False)
    meeting = db.relationship(
        'Meeting',
        backref=db.backref('participants', lazy='dynamic'))

    title = db.Column(db.String(8), nullable=False)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(64), nullable=False)

    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id'),
        nullable=True)
    user = db.relationship(
        'User',
        backref=db.backref('participants', lazy='dynamic'))

    category_id = db.Column(
        db.Integer, db.ForeignKey('category.id'),
        nullable=False)
    category = db.relationship(
        'Category',
        backref=db.backref('participants', lazy='dynamic'))

    def __repr__(self):
        return '{} {}'.format(self.first_name, self.last_name)


class CustomField(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    meeting_id = db.Column(
        db.Integer, db.ForeignKey('meeting.id'),
        nullable=False)
    meeting = db.relationship(
        'Meeting',
        backref=db.backref('custom_fields', lazy='dynamic'))

    type = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return '{} {}'.format(self.type, self.meeting.acronym)


class CustomFieldChoice(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    custom_field_id = db.Column(
        db.Integer, db.ForeignKey('custom_field.id'),
        nullable=False)
    custom_field = db.relationship(
        'CustomField',
        backref=db.backref('custom_field_choices', lazy='dynamic'))

    value_id = db.Column(
        db.Integer, db.ForeignKey('translation.id'),
        nullable=False)
    value = db.relationship(
        'Translation',
        backref=db.backref('custom_field_choices', lazy='dynamic'))

    def __repr__(self):
        return '{}'.format(self.value.english)


class CustomFieldValue(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    custom_field_id = db.Column(
        db.Integer, db.ForeignKey('custom_field.id'),
        nullable=False)
    custom_field = db.relationship(
        'CustomField',
        backref=db.backref('custom_field_values', lazy='dynamic'))

    participant_id = db.Column(
        db.Integer, db.ForeignKey('participant.id'),
        nullable=False)
    participant = db.relationship(
        'Participant',
        backref=db.backref('custom_field_values', lazy='dynamic'))

    value = db.Column(db.String(64), nullable=False)

    choice_id = db.Column(
        db.Integer, db.ForeignKey('custom_field_choice.id'),
        nullable=True)
    choice = db.relationship(
        'CustomFieldChoice',
        backref=db.backref('custom_field_values', lazy='dynamic'))

    def __repr__(self):
        return '{}'.format(self.value)


class MediaPaticipant(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    meeting_id = db.Column(
        db.Integer, db.ForeignKey('meeting.id'),
        nullable=False)
    meeting = db.relationship(
        'Meeting',
        backref=db.backref('media_participants', lazy='dynamic'))

    title = db.Column(db.String(8), nullable=False)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(64), nullable=False)

    category_id = db.Column(
        db.Integer, db.ForeignKey('category.id'),
        nullable=False)
    category = db.relationship(
        'Category',
        backref=db.backref('media_participants', lazy='dynamic'))

    def __repr__(self):
        return '{} {}'.format(self.first_name, self.last_name)


class Meeting(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    title_id = db.Column(db.Integer, db.ForeignKey('translation.id'),
                         nullable=False)

    title = db.relationship('Translation', foreign_keys=title_id)

    acronym = db.Column(db.String(16), nullable=False,
                        info={'label': 'Acronym'})

    meeting_type = db.Column(db.String(3), nullable=False)

    date_start = db.Column(db.Date, nullable=False,
                           info={'label': 'Start Date'})

    date_end = db.Column(db.Date, nullable=False,
                         info={'label': 'End Date'})

    venue_address = db.Column(db.String(128),
                              info={'label': 'Address'})

    venue_city_id = db.Column(db.Integer, db.ForeignKey('translation.id'),
                              nullable=False)

    venue_city = db.relationship('Translation', foreign_keys=venue_city_id)

    venue_country = db.Column(CountryType, nullable=False,
                              info={'label': 'Country'})

    venue_state = db.Column(db.String(128), info={'label': 'State/Province'})

    venue_code = db.Column(db.String(16), info={'label': 'Zip code'})

    admin_name = db.Column(db.String(32))

    admin_email = db.Column(db.String(32))

    media_admin_name = db.Column(db.String(32))

    media_admin_email = db.Column(db.String(32))

    online_registration = db.Column(
        db.Boolean, nullable=False, default=True,
        info={'label': 'Allow Online Registration'})

    def __repr__(self):
        return '{}'.format(self.title)


class Category(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name_id = db.Column(
        db.Integer, db.ForeignKey('translation.id'),
        nullable=False)
    name = db.relationship(
        'Translation',
        backref=db.backref('categories', lazy='dynamic'))

    color = db.Column(db.String(16), nullable=False)
    background = db.Column(db.String(32), nullable=False)
    type = db.Column(db.String(32), nullable=False)

    meeting_id = db.Column(
        db.Integer, db.ForeignKey('meeting.id'),
        nullable=False)
    meeting = db.relationship(
        'Meeting',
        backref=db.backref('categories', lazy='dynamic'))

    def __repr__(self):
        return '{} {}'.format(self.meeting.acronym, self.name.english)


class CategoryDefault(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    name_id = db.Column(
        db.Integer, db.ForeignKey('translation.id'),
        nullable=False)
    name = db.relationship(
        'Translation',
        backref=db.backref('default_categories', lazy='dynamic'))
    color = db.Column(db.String(16), nullable=False)
    background = db.Column(db.String(32), nullable=False)
    type = db.Column(db.String(32), nullable=False)

    def __repr__(self):
        return '{}'.format(self.name.english)


class Translation(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    english = db.Column(db.Text, nullable=False,
                        info={'label': 'English'})
    french = db.Column(db.Text, info={'label': 'French'})
    spanish = db.Column(db.Text, info={'label': 'Spanish'})

    def __repr__(self):
        return '{}'.format(self.english)


class Phrase(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False)
    descpription_translation_id = db.Column(
        db.Integer, db.ForeignKey('translation.id'),
        nullable=False)
    description = db.relationship(
        'Translation',
        backref=db.backref('phrases', lazy='dynamic'))

    meeting_id = db.Column(
        db.Integer, db.ForeignKey('meeting.id'),
        nullable=False)
    meeting = db.relationship(
        'Meeting',
        backref=db.backref('phrases', lazy='dynamic'))

    group = db.Column(db.String(32), nullable=True)
    sort = db.Column(db.Integer, default=0)

    def __repr__(self):
        return '{}'.format(self.name)
