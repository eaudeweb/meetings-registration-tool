import json
from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash
from flask.ext.sqlalchemy import SQLAlchemy

from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy_utils import ChoiceType, CountryType, EmailType
from sqlalchemy_utils import generates
from sqlalchemy.types import TypeDecorator, String

from mrt.utils import slugify
from mrt.definitions import (
    CATEGORIES, MEETING_TYPES, CUSTOM_FIELDS, PERMISSIONS,
)


db = SQLAlchemy()


class JSONEncodedDict(TypeDecorator):
    impl = String

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(EmailType, unique=True, nullable=False,
                      info={'label': 'Email'})
    password = db.Column(db.String(128), nullable=True)
    recover_token = db.Column(db.String(64))
    recover_time = db.Column(db.DateTime)

    def __repr__(self):
        return '%s' % self.email

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True if self.password else False

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)

    def token_is_active(self):
        return (datetime.now() - self.recover_time).total_seconds() < 86400

    def has_perms(self, perms, meeting_id=None):
        user_roles = RoleUser.query.filter_by(
            user_id=self.id, meeting_id=meeting_id)
        for user_role in user_roles:
            if set(user_role.role.permissions).issuperset(perms):
                return True
        return False


class Staff(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64), nullable=True, info={'label': 'Title'})
    full_name = db.Column(db.String(128), nullable=False,
                          info={'label': 'Full Name'})

    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id'),
        nullable=False)
    user = db.relationship(
        'User',
        backref=db.backref('staff', uselist=False))

    @property
    def user_role(self):
        return RoleUser.query.filter_by(user=self.user, meeting=None).first()

    def __repr__(self):
        return self.full_name or self.user.email


class Role(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False,
                     info={'label': 'Name'})
    permissions = db.Column(JSONEncodedDict, nullable=False)

    @property
    def permissions_details(self):
        return ', '.join(dict(PERMISSIONS).get(k, k) for k in self.permissions)

    def __repr__(self):
        return self.name


class RoleUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(
        db.Integer, db.ForeignKey('meeting.id'),
        nullable=True)
    meeting = db.relationship(
        'Meeting',
        backref=db.backref('role_users', lazy='dynamic', cascade="delete"))

    role_id = db.Column(
        db.Integer, db.ForeignKey('role.id'),
        nullable=False)
    role = db.relationship(
        'Role',
        backref=db.backref('role_users', lazy='dynamic'))

    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id'),
        nullable=False)
    user = db.relationship(
        'User',
        backref=db.backref('role_users', lazy='dynamic'))

    @property
    def staff(self):
        return self.user.staff

    def __repr__(self):
        return '%s %s' % (self.user, self.role)


class Participant(db.Model):

    TITLE_CHOICES = (
        ('Ms', 'Ms'),
        ('Mr', 'Mr'),
    )
    LANGUAGE_CHOICES = (
        ('en', 'English'),
        ('es', 'Spanish'),
        ('fr', 'French'),
    )

    id = db.Column(db.Integer, primary_key=True)

    meeting_id = db.Column(
        db.Integer, db.ForeignKey('meeting.id'),
        nullable=False)
    meeting = db.relationship(
        'Meeting',
        backref=db.backref('participants', lazy='dynamic', cascade="delete"))

    title = db.Column(ChoiceType(TITLE_CHOICES), nullable=False,
                      info={'label': 'Title'})

    first_name = db.Column(db.String(64), nullable=False,
                           info={'label': 'Given name'})

    last_name = db.Column(db.String(64), nullable=False,
                          info={'label': 'Family name'})

    email = db.Column(db.String(64), nullable=False,
                      info={'label': 'Email'})

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

    language = db.Column(ChoiceType(LANGUAGE_CHOICES), nullable=False,
                         info={'label': 'Working language'}, default=u'en')
    country = db.Column(CountryType, nullable=False,
                        info={'label': 'Country'})

    def __repr__(self):
        return self.name

    @property
    def name(self):
        return '%s %s %s' % (self.title.value, self.first_name,
                             self.last_name)


class CustomField(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    slug = db.Column(db.String(255))

    meeting_id = db.Column(
        db.Integer, db.ForeignKey('meeting.id'),
        nullable=False)
    meeting = db.relationship(
        'Meeting',
        backref=db.backref('custom_fields', lazy='dynamic', cascade="delete"))

    label_id = db.Column(
        db.Integer, db.ForeignKey('translation.id'),
        nullable=False)

    label = db.relationship('Translation')

    field_type = db.Column(ChoiceType(CUSTOM_FIELDS), nullable=False,
                           info={'label': 'Field type'})

    required = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return self.label.english

    @generates('slug')
    def _create_slug(self):
        return slugify(self.label.english)


class CustomFieldChoice(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    custom_field_id = db.Column(
        db.Integer(), db.ForeignKey('custom_field.id'),
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
        return self.value.english


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
        return self.value


class MediaParticipant(db.Model):

    TITLE_CHOICES = (
        ('Ms', 'Ms'),
        ('Mr', 'Mr'),
    )

    id = db.Column(db.Integer, primary_key=True)

    meeting_id = db.Column(
        db.Integer, db.ForeignKey('meeting.id'),
        nullable=False)
    meeting = db.relationship(
        'Meeting',
        backref=db.backref('media_participants', lazy='dynamic',
                           cascade="delete"))

    title = db.Column(ChoiceType(TITLE_CHOICES), nullable=False,
                      info={'label': 'Title'})
    first_name = db.Column(db.String(64), nullable=False,
                           info={'label': 'Given name'})
    last_name = db.Column(db.String(64), nullable=False,
                          info={'label': 'Family name'})
    email = db.Column(db.String(64), nullable=False,
                      info={'label': 'Email'})

    category_id = db.Column(
        db.Integer, db.ForeignKey('category.id'),
        nullable=False)
    category = db.relationship(
        'Category',
        backref=db.backref('media_participants', lazy='dynamic'))

    def __repr__(self):
        return '%s %s' % (self.first_name, self.last_name)

    @property
    def name(self):
        return '%s %s %s' % (self.title.value, self.first_name,
                             self.last_name)


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

    owner_id = db.Column(db.Integer, db.ForeignKey('staff.id'))

    owner = db.relationship('Staff', foreign_keys=owner_id)

    online_registration = db.Column(
        db.Boolean, nullable=False, default=True,
        info={'label': 'Allow Online Registration'})

    def __repr__(self):
        return self.title.english


class CategoryMixin(object):

    id = db.Column(db.Integer, primary_key=True)

    @declared_attr
    def title_id(cls):
        return db.Column(db.Integer, db.ForeignKey('translation.id'),
                         nullable=False)

    @declared_attr
    def title(cls):
        return db.relationship('Translation')

    color = db.Column(db.String(7), nullable=False, info={'label': 'Color'})

    background = db.Column(db.String(64))

    type = db.Column(ChoiceType(CATEGORIES), nullable=False,
                     info={'label': 'Category Type'})

    sort = db.Column(db.Integer, default=0)


class Category(CategoryMixin, db.Model):

    __tablename__ = 'category'

    meeting_id = db.Column(
        db.Integer, db.ForeignKey('meeting.id'),
        nullable=False)

    meeting = db.relationship(
        'Meeting',
        backref=db.backref('categories', lazy='dynamic', cascade="delete"))

    def __repr__(self):
        return self.title.english


class CategoryDefault(CategoryMixin, db.Model):

    __tablename__ = 'category_default'

    def __repr__(self):
        return self.title.english


class Translation(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    english = db.Column(db.Text, nullable=False,
                        info={'label': 'English'})
    french = db.Column(db.Text, info={'label': 'French'})
    spanish = db.Column(db.Text, info={'label': 'Spanish'})

    def __repr__(self):
        return self.english

    def __init__(self, english=None):
        self.english = english


class PhraseMixin(object):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False)

    @declared_attr
    def description_id(cls):
        return db.Column(db.Integer, db.ForeignKey('translation.id'))

    @declared_attr
    def description(cls):
        return db.relationship('Translation')

    group = db.Column(db.String(32), nullable=True)
    sort = db.Column(db.Integer, default=0)

    def __repr__(self):
        return self.name


class Phrase(PhraseMixin, db.Model):

    __tablename__ = 'phrase'

    meeting_id = db.Column(
        db.Integer, db.ForeignKey('meeting.id'),
        nullable=False)
    meeting = db.relationship(
        'Meeting',
        backref=db.backref('phrases', lazy='dynamic', cascade="delete"))


class PhraseDefault(PhraseMixin, db.Model):

    __tablename__ = 'phrase_default'

    meeting_type = db.Column(ChoiceType(MEETING_TYPES), nullable=False,
                             info={'label': 'Meeting Type'})
