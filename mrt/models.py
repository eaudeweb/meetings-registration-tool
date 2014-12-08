from datetime import datetime
import json

from werkzeug.security import generate_password_hash, check_password_hash

from flask import g, render_template, current_app as app
from flask.ext.babel import get_locale, Locale
from flask.ext.babel import gettext as _
from flask.ext.babel import lazy_gettext as __
from flask.ext.sqlalchemy import SQLAlchemy, BaseQuery
from flask_redis import Redis

from jinja2.exceptions import TemplateNotFound

from wtforms.fields import DateField
from sqlalchemy import cast
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.types import TypeDecorator, String
from sqlalchemy_utils import ChoiceType, CountryType, EmailType
from sqlalchemy_utils import generates

from mrt.definitions import (
    PERMISSIONS, NOTIFICATION_TYPES, REPRESENTING_REGIONS,
    CATEGORY_REPRESENTING)
from mrt.utils import slugify, copy_attributes, duplicate_uploaded_file
from mrt.utils import unlink_participant_photo


db = SQLAlchemy()

redis_store = Redis()


class ParticipantQuery(BaseQuery):

    def active(self):
        return self.filter(Participant.deleted == False)


class CustomFieldQuery(BaseQuery):

    def for_registration(self):
        return self.filter_by(visible_on_registration_form=True)


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
    active = db.Column(db.Boolean, nullable=False, default=True)
    is_superuser = db.Column(db.Boolean, nullable=False, default=False,
                             info={'label': 'Superuser'})

    def __repr__(self):
        return '%s' % self.email

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True if (self.password and self.active) else False

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

    def get_default(self):
        return (self.participants.filter(
            Participant.meeting.has(meeting_type_slug=Meeting.DEFAULT_TYPE))
            .scalar())


class UserNotification(db.Model):

    __table_args__ = (
        db.UniqueConstraint('user_id', 'meeting_id', 'notification_type'),)

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id'),
        nullable=False)
    user = db.relationship(
        'User',
        backref=db.backref('user_notifications', lazy='dynamic'))

    meeting_id = db.Column(
        db.Integer, db.ForeignKey('meeting.id'),
        nullable=False)
    meeting = db.relationship(
        'Meeting',
        backref=db.backref('user_notifications',
                           lazy='dynamic', cascade="delete"))

    notification_type = db.Column(db.String(32), nullable=False)

    def __repr__(self):
        return '%s %s' % (self.user, self.notification_type)

    @property
    def type_detail(self):
        return dict(NOTIFICATION_TYPES).get(self.notification_type,
                                            self.notification_type)


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

    def get_permissions(self):
        return [dict(PERMISSIONS).get(k, k) for k in self.permissions]

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

    __table_args__ = (
        db.UniqueConstraint('registration_token'),)

    query_class = ParticipantQuery

    TITLE_CHOICES = (
        ('Ms', 'Ms'),
        ('Mr', 'Mr'),
    )
    LANGUAGE_CHOICES = (
        ('English', __('English')),
        ('Spanish', __('Spanish')),
        ('French', __('French')),
    )
    PARTICIPANT = u'participant'
    MEDIA = 'media'
    PARTICIPANT_TYPE_CHOICES = (
        (PARTICIPANT, __('Participant')),
        (MEDIA, __('Media')),
    )

    EXCLUDE_WHEN_COPYING = ('meeting_id', 'category_id', 'registration_token',)

    id = db.Column(db.Integer, primary_key=True)

    meeting_id = db.Column(db.Integer, db.ForeignKey('meeting.id'),
                           nullable=True)
    meeting = db.relationship(
        'Meeting',
        backref=db.backref('participants', lazy='dynamic', cascade="delete"))

    title = db.Column(ChoiceType(TITLE_CHOICES), nullable=False,
                      info={'label': _('Title')})

    first_name = db.Column(db.String(64), nullable=False,
                           info={'label': _('Given name')})

    last_name = db.Column(db.String(64), nullable=False,
                          info={'label': _('Family name')})

    email = db.Column(db.String(64), nullable=False,
                      info={'label': _('Email')})

    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id'),
        nullable=True)
    user = db.relationship(
        'User',
        backref=db.backref('participants', lazy='dynamic'))

    category_id = db.Column(
        db.Integer, db.ForeignKey('category.id'),
        nullable=True)
    category = db.relationship(
        'Category',
        backref=db.backref('participants', lazy='dynamic'))

    language = db.Column(ChoiceType(LANGUAGE_CHOICES), nullable=False,
                         info={'label': _('Working language')}, default=u'en')

    country = db.Column(CountryType, nullable=False,
                        info={'label': _('Country')})

    deleted = db.Column(db.Boolean, default=False)

    represented_country = db.Column(
        CountryType,
        info={'label': _('Country represented')})

    represented_region = db.Column(
        ChoiceType(REPRESENTING_REGIONS),
        info={'label': _('Representing region')})

    represented_organization = db.Column(
        db.String(64),
        info={'label': _('Organization represented')})

    attended = db.Column(db.Boolean, default=False,
                         info={'label': _('Attended')})

    verified = db.Column(db.Boolean, default=False,
                         info={'label': _('Verified')})

    credentials = db.Column(db.Boolean, default=False,
                            info={'label': _('Credentials')})

    registration_token = db.Column(db.String(64), nullable=True)

    participant_type = db.Column(
        ChoiceType(PARTICIPANT_TYPE_CHOICES),
        nullable=False, default=PARTICIPANT,
        info={'label': _('Participant type')})

    def __repr__(self):
        return self.name

    @property
    def name(self):
        return '%s %s %s' % (self.title.value, self.first_name,
                             self.last_name)

    @property
    def lang(self):
        return self.language.value.lower()

    @property
    def representing(self):
        if not self.category.representing:
            return ''
        template_name = str(app.config['REPRESENTING_TEMPLATES']
                            / self.category.representing.code)
        try:
            template = app.jinja_env.get_template(template_name)
        except TemplateNotFound:
            return ''
        return render_template(template, participant=self)

    @property
    def photo(self):
        field = g.meeting.photo_field
        if field:
            photo = (
                field.custom_field_values
                .filter_by(participant_id=self.id).first())
            return photo.value if photo else None
        return None

    def _clone_custom_field(self, custom_field):
        cf = (CustomField.query
              .filter_by(meeting=self.default_meeting)
              .filter_by(slug=custom_field.slug)
              .scalar())
        if not cf:
            cf = copy_attributes(CustomField(), custom_field)
            cf.label = Translation(english=custom_field.label.english)
            cf.meeting = self.default_meeting
            db.session.add(cf)
        return cf

    def _clone_custom_field_value(self, participant, custom_field_clone,
                                  custom_field_value):
        cfv = (CustomFieldValue.query
               .filter_by(custom_field=custom_field_clone)
               .filter_by(participant=participant)
               .scalar())
        if cfv:
            if custom_field_clone.field_type == CustomField.IMAGE:
                unlink_participant_photo(cfv.value)
            cfv = copy_attributes(cfv, custom_field_value)
        else:
            cfv = copy_attributes(CustomFieldValue(), custom_field_value)
            cfv.custom_field_id = custom_field_clone.id
            cfv.participant_id = participant.id
            db.session.add(cfv)
        if custom_field_clone.field_type == CustomField.IMAGE:
            filename = duplicate_uploaded_file(custom_field_value.value,
                                               'custom')
            cfv.value = filename.basename()
        return cfv

    def _add_primary_custom_fields_for_default_meeting(self):
        from mrt.forms.meetings import ParticipantDummyForm
        from mrt.forms.meetings import add_custom_fields_for_meeting
        nr_fields = len(list(ParticipantDummyForm()))
        count = (
            CustomField.query.filter_by(meeting=self.default_meeting)
            .filter_by(is_primary=True)
        ).count()
        if not nr_fields == count:
            add_custom_fields_for_meeting(self.default_meeting)

    def clone(self):
        self.default_meeting = Meeting.get_default()
        participant = copy_attributes(
            Participant(), self, with_relations=True,
            exclude=self.EXCLUDE_WHEN_COPYING)
        participant.meeting = self.default_meeting
        db.session.add(participant)
        db.session.flush()

        # add primary custom fields for default meeting
        self._add_primary_custom_fields_for_default_meeting()

        for cfv in self.custom_field_values.all():
            cf_clone = self._clone_custom_field(cfv.custom_field)
            db.session.flush()
            self._clone_custom_field_value(participant, cf_clone, cfv)
        return participant

    def update(self, source):
        self.default_meeting = Meeting.get_default()
        participant = copy_attributes(self, source, with_relations=True,
                                      exclude=self.EXCLUDE_WHEN_COPYING)
        for cfv in source.custom_field_values.all():
            cf_clone = self._clone_custom_field(cfv.custom_field)
            db.session.flush()
            self._clone_custom_field_value(participant, cf_clone, cfv)
        return participant


class CustomField(db.Model):

    TEXT = 'text'
    IMAGE = 'image'
    EMAIL = 'email'
    CHECKBOX = 'checkbox'
    SELECT = 'select'
    COUNTRY = 'country'
    CATEGORY = 'category'

    CUSTOM_FIELDS = (
        (TEXT, 'Text Field'),
        (IMAGE, 'Image Field'),
        (EMAIL, 'Email Field'),
        (CHECKBOX, 'Checkbox Field'),
        (SELECT, 'Select Field'),
        (COUNTRY, 'Country Field'),
        (CATEGORY, 'Category Field'),
    )

    PARTICIPANT = u'participant'
    MEDIA = 'media'
    CUSTOM_FIELD_TYPE_CHOICES = (
        (PARTICIPANT, 'Participant'),
        (MEDIA, 'Media'),
    )

    query_class = CustomFieldQuery

    __table_args__ = (
        db.UniqueConstraint('meeting_id', 'slug', 'custom_field_type'),)

    id = db.Column(db.Integer, primary_key=True)

    slug = db.Column(db.String(255))

    meeting_id = db.Column(
        db.Integer, db.ForeignKey('meeting.id'))
    meeting = db.relationship(
        'Meeting',
        foreign_keys=meeting_id,
        backref=db.backref('custom_fields', lazy='dynamic', cascade="delete"))

    label_id = db.Column(
        db.Integer, db.ForeignKey('translation.id'),
        nullable=False)

    label = db.relationship('Translation')

    description = db.Column(db.String(512), info={'label': 'Description'})

    field_type = db.Column(ChoiceType(CUSTOM_FIELDS), nullable=False,
                           info={'label': 'Field type'})

    required = db.Column(db.Boolean, default=False,
                         info={'label': 'Required'})

    sort = db.Column(db.Integer, default=0)

    is_primary = db.Column(db.Boolean, default=False)

    visible_on_registration_form = db.Column(
        db.Boolean, default=False,
        info={'label': 'Visible on registration form'})

    custom_field_type = db.Column(
        ChoiceType(CUSTOM_FIELD_TYPE_CHOICES),
        nullable=False, default=PARTICIPANT,
        info={'label': 'Custom field type'})

    def __repr__(self):
        return self.label.english

    @generates('slug')
    def _create_slug(self):
        return self.slug or slugify(self.label.english)

    def get_or_create_value(self, participant):
        with db.session.no_autoflush:
            value = (self.custom_field_values
                     .filter_by(participant=participant)
                     .first())
        return value or CustomFieldValue(custom_field=self,
                                         participant=participant)


class CustomFieldValue(db.Model):

    __table_args__ = (
        db.UniqueConstraint('custom_field_id', 'participant_id'),)

    id = db.Column(db.Integer, primary_key=True)

    custom_field_id = db.Column(
        db.Integer, db.ForeignKey('custom_field.id'),
        nullable=False)
    custom_field = db.relationship(
        'CustomField',
        backref=db.backref('custom_field_values', lazy='dynamic',
                           cascade="delete"))

    participant_id = db.Column(
        db.Integer, db.ForeignKey('participant.id'),
        nullable=False)
    participant = db.relationship(
        'Participant',
        backref=db.backref('custom_field_values', lazy='dynamic',
                           cascade="delete"))

    value = db.Column(db.String(64), nullable=False)

    choice_id = db.Column(
        db.Integer, db.ForeignKey('custom_field_choice.id'),
        nullable=True)
    choice = db.relationship(
        'CustomFieldChoice',
        backref=db.backref('custom_field_values', lazy='dynamic'))

    def __repr__(self):
        return self.value


class CustomFieldChoice(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    custom_field_id = db.Column(
        db.Integer(), db.ForeignKey('custom_field.id'),
        nullable=False)
    custom_field = db.relationship(
        'CustomField',
        backref=db.backref('custom_field_choices', lazy='dynamic',
                           cascade='delete'))

    value_id = db.Column(
        db.Integer, db.ForeignKey('translation.id'),
        nullable=False)
    value = db.relationship(
        'Translation',
        backref=db.backref('custom_field_choices', lazy='dynamic',))

    def __repr__(self):
        return self.value.english


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

    DEFAULT_TYPE = 'def'

    id = db.Column(db.Integer, primary_key=True)

    title_id = db.Column(db.Integer, db.ForeignKey('translation.id'),
                         nullable=False)

    title = db.relationship('Translation', foreign_keys=title_id)

    badge_header_id = db.Column(db.Integer, db.ForeignKey('translation.id'))

    badge_header = db.relationship('Translation', foreign_keys=badge_header_id)

    acronym = db.Column(db.String(16), nullable=False,
                        info={'label': 'Acronym'})

    meeting_type_slug = db.Column(
        'meeting_type', db.String(16), db.ForeignKey('meeting_type.slug'),
        nullable=False)
    meeting_type = db.relationship(
        'MeetingType', backref=db.backref('meetings', lazy='dynamic'))

    date_start = db.Column(db.Date, nullable=False,
                           info={'label': 'Start Date',
                                 'form_field_class': DateField})

    date_end = db.Column(db.Date, nullable=False,
                         info={'label': 'End Date',
                               'form_field_class': DateField})

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

    settings = db.Column(JSONEncodedDict, nullable=True)

    photo_field_id = db.Column(db.Integer,
                               db.ForeignKey('custom_field.id',
                                             ondelete="SET NULL",
                                             use_alter=True,
                                             name='fk_photo_field'),
                               nullable=True)

    photo_field = db.relationship('CustomField',
                                  foreign_keys=photo_field_id,
                                  post_update=True)

    @property
    def media_participant_enabled(self):
        return (self.settings and
                self.settings.get('media_participant_enabled', False))

    @classmethod
    def get_default(cls):
        return cls.query.filter_by(
            meeting_type_slug=Meeting.DEFAULT_TYPE).one()

    def __repr__(self):
        return self.title.english


class CategoryMixin(object):

    PARTICIPANT = u'participant'
    MEDIA = u'media'
    CATEGORY_TYPES = (
        (PARTICIPANT, 'Category for participants'),
        (MEDIA, 'Category for media participants'),
    )

    CATEGORY_GROUPS = (
        ('country', 'Group category by country'),
        ('organization', 'Group category by organization'),
    )

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

    representing = db.Column(ChoiceType(CATEGORY_REPRESENTING),
                             info={'label': 'Representing'})

    category_type = db.Column(ChoiceType(CATEGORY_TYPES),
                              nullable=False, default=PARTICIPANT,
                              info={'label': 'Category type'})

    group = db.Column(ChoiceType(CATEGORY_GROUPS),
                      info={'label': 'Group'})

    sort = db.Column(db.Integer, default=0)

    visible_on_registration_form = db.Column(
        db.Boolean, default=False,
        info={'label': 'Visible on registration form'})

    def __repr__(self):
        locale = get_locale() or Locale('en')
        lang = {'en': 'english', 'fr': 'french', 'es': 'spanish'}.get(
            locale.language, 'english')
        return getattr(self.title, lang, '') or ''


class Category(CategoryMixin, db.Model):

    __tablename__ = 'category'

    meeting_id = db.Column(
        db.Integer, db.ForeignKey('meeting.id'),
        nullable=False)

    meeting = db.relationship(
        'Meeting',
        backref=db.backref('categories', lazy='dynamic', cascade="delete"))


class CategoryDefault(CategoryMixin, db.Model):

    __tablename__ = 'category_default'


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

    ACK_EMAIL = 'Acknowledge email'
    SUBJECT = 'Subject'
    BODY = 'Body'

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

    meeting_type_slug = db.Column(
        'meeting_type', db.String(16), db.ForeignKey('meeting_type.slug'),
        nullable=False)
    meeting_type = db.relationship(
        'MeetingType', backref=db.backref(
            'default_phrases', cascade='all,delete'))


class MeetingType(db.Model):
    __tablename__ = 'meeting_type'
    slug = db.Column(db.String(16), primary_key=True, info={'label': 'Slug'})
    label = db.Column(db.String(128), nullable=False, info={'label': 'Label'})
    default = db.Column(db.Boolean, nullable=False, default=False)

    def load_default_phrases(self):
        with open(app.config['DEFAULT_PHRASES_PATH'], 'r') as f:
            default_phrases = json.load(f)
        self.default_phrases += [PhraseDefault(**d) for d in default_phrases]


class MailLog(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    meeting_id = db.Column(
        db.Integer, db.ForeignKey('meeting.id'),
        nullable=False)
    meeting = db.relationship(
        'Meeting',
        backref=db.backref('mails', lazy='dynamic', cascade='delete'))

    to_id = db.Column(
        db.Integer, db.ForeignKey('participant.id'),
        nullable=False)
    to = db.relationship(
        'Participant',
        backref=db.backref('mails', lazy='dynamic', cascade='delete'))

    subject = db.Column(db.String(128), nullable=False)
    message = db.Column(db.Text, nullable=False)
    date_sent = db.Column(db.DateTime)

    def __repr__(self):
        return self.to.email


class ActivityLog(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    staff_id = db.Column(
        db.Integer, db.ForeignKey('staff.id'),
        nullable=True)
    staff = db.relationship(
        'Staff',
        backref=db.backref('activities', lazy='dynamic', cascade='delete'))

    meeting_id = db.Column(
        db.Integer, db.ForeignKey('meeting.id'),
        nullable=False)
    meeting = db.relationship(
        'Meeting',
        backref=db.backref('activities', lazy='dynamic', cascade='delete'))

    participant_id = db.Column(
        db.Integer, db.ForeignKey('participant.id'),
        nullable=False)
    participant = db.relationship(
        'Participant',
        backref=db.backref('activities', lazy='dynamic'))

    date = db.Column(db.DateTime, nullable=False)
    action = db.Column(db.String(64), nullable=False)

    def __repr__(self):
        return '%s %s' % (self.staff.full_name, self.action)


class Job(db.Model):

    QUEUED = u'queued'
    FINISHED = u'finished'
    FAILED = u'failed'
    STARTED = u'started'

    STATUS = (
        (QUEUED, 'Queued'),
        (FINISHED, 'Finished'),
        (FAILED, 'Failed'),
        (STARTED, 'Started'),
    )

    PRINTOUTS_QUEUE = 'printouts'

    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(32))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                        nullable=False)
    user = db.relationship('User', backref=db.backref('jobs', uselist=False))
    meeting_id = db.Column(db.Integer, db.ForeignKey('meeting.id'))
    meeting = db.relationship('Meeting',
                              backref=db.backref('jobs', uselist=False))
    date = db.Column(db.DateTime, nullable=False)
    status = db.Column(ChoiceType(STATUS), nullable=False)
    queue = db.Column(db.String(32))
    result = db.Column(db.String(512))

    @property
    def is_finished(self):
        return self.status == self.FINISHED

    @property
    def is_failed(self):
        return self.status == self.FAILED

    @property
    def is_started(self):
        return self.status == self.STARTED


def get_or_create_role(name):
    role = Role.query.filter_by(name=name).first()
    if not role:
        role = Role(name=name, permissions=[p[0] for p in PERMISSIONS])
        db.session.add(role)
    return role


def search_for_participant(search, queryset=None):
    queryset = queryset or Participant.query.active()
    if not isinstance(search, basestring):
        search = str(search)
    return queryset.filter(
        (cast(Participant.id, String) == search) |
        Participant.first_name.contains(search) |
        Participant.last_name.contains(search) |
        Participant.email.contains(search) |
        Participant.category.has(
            Category.title.has(Translation.english.contains(search))
        )
    )


def get_participants_full(meeting_id):
    qs = (
        Participant.query
        .join(Participant.custom_field_values)
        .join(CustomFieldValue.custom_field)
        .with_entities(Participant,
                       CustomField.slug,
                       CustomFieldValue.value)
        .filter_by(meeting_id=meeting_id).active()
        .order_by(Participant.id.desc())
    )

    last_participant = None
    for participant, slug, value in qs:
        if last_participant and participant.id != last_participant.id:
            yield last_participant
            last_participant = None

        if not last_participant:
            last_participant = participant
        setattr(last_participant, slug, value)

    if last_participant:
        yield last_participant
