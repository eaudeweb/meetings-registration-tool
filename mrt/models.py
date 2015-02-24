from datetime import datetime
import json

from werkzeug.security import generate_password_hash, check_password_hash

from flask import g, render_template, current_app as app, url_for
from flask.ext.babel import get_locale, Locale
from flask.ext.babel import gettext as _
from flask.ext.babel import lazy_gettext as __
from flask.ext.sqlalchemy import SQLAlchemy, BaseQuery
from flask_redis import Redis
from jinja2.exceptions import TemplateNotFound

from sqlalchemy import cast
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.types import TypeDecorator, String
from sqlalchemy_utils import ChoiceType, CountryType, EmailType
from sqlalchemy_utils import generates
from wtforms.fields import DateField

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

    def participants(self):
        return self.filter(
            Participant.participant_type == Participant.PARTICIPANT)

    def media_participants(self):
        return self.filter(Participant.participant_type == Participant.MEDIA)

    def default_participants(self):
        return self.filter(Participant.participant_type == Participant.DEFAULT)

    def default_media_participants(self):
        return self.filter(
            Participant.participant_type == Participant.DEFAULT_MEDIA)

    def current_meeting(self):
        return self.filter(Participant.meeting == g.meeting).active()


class CustomFieldQuery(BaseQuery):

    def for_registration(self):
        return self.filter_by(visible_on_registration_form=True)


class MeetingTypeQuery(BaseQuery):

    def default(self):
        return self.filter_by(default=True).one()

    def ignore_def(self):
        return self.filter(MeetingType.default != True)


class MeetingQuery(BaseQuery):

    def ignore_def(self):
        return self.join(MeetingType).filter(MeetingType.default != True)


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
    password = db.Column(db.String(128))
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

    def has_perms(self, perms, meeting_id):
        user_roles = RoleUser.query.filter_by(
            user_id=self.id, meeting_id=meeting_id)
        for user_role in user_roles:
            if set(user_role.role.permissions).intersection(perms):
                return True
        return False

    def get_default(self, participant_type):
        return (
            self.participants.filter(
                Participant.meeting.has(Meeting.meeting_type.has(default=True))
            )
            .filter(Participant.participant_type == participant_type)
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
    title = db.Column(db.String(64), info={'label': 'Title'})
    full_name = db.Column(db.String(128), nullable=False,
                          info={'label': 'Full Name'})

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(
        'User',
        backref=db.backref('staff', uselist=False, cascade='delete'))

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
        nullable=False)
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
    DEFAULT = 'default'
    DEFAULT_MEDIA = 'default_media'
    PARTICIPANT_TYPE_CHOICES = (
        (PARTICIPANT, __('Participant')),
        (MEDIA, __('Media')),
        (DEFAULT, __('Default')),
        (DEFAULT_MEDIA, __('Default Media')),
    )

    EXCLUDE_WHEN_COPYING = ('meeting_id', 'category_id', 'registration_token',
                            'participant_type',)

    id = db.Column(db.Integer, primary_key=True)

    meeting_id = db.Column(db.Integer, db.ForeignKey('meeting.id'))
    meeting = db.relationship(
        'Meeting',
        backref=db.backref('participants', lazy='dynamic', cascade="delete"))

    title = db.Column(ChoiceType(TITLE_CHOICES), nullable=False,
                      info={'label': _('Title')})

    first_name = db.Column(db.String(64), nullable=False,
                           info={'label': _('Given name')})

    last_name = db.Column(db.String(64), nullable=False,
                          info={'label': _('Family name')})

    email = db.Column(db.String(128), nullable=False,
                      info={'label': _('Email')})

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship(
        'User',
        backref=db.backref('participants', lazy='dynamic'))

    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    category = db.relationship(
        'Category',
        backref=db.backref('participants', lazy='dynamic'))

    language = db.Column(ChoiceType(LANGUAGE_CHOICES), nullable=False,
                         info={'label': _('Working language')},
                         default=u'English')

    country = db.Column(CountryType, info={'label': _('Country')})

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

    registration_token = db.Column(db.String(64))

    participant_type = db.Column(
        ChoiceType(PARTICIPANT_TYPE_CHOICES),
        nullable=False, default=PARTICIPANT,
        info={'label': _('Participant type')})

    def __repr__(self):
        return self.name

    def get_absolute_url(self):
        url = {
            self.PARTICIPANT: 'meetings.participant_detail',
            self.MEDIA: 'meetings.media_participant_detail',
            self.DEFAULT: 'meetings.default_participant_detail',
            self.DEFAULT_MEDIA: 'meetings.default_media_participant_detail',
        }.get(self.participant_type.code, 'meetings.participant_detail')
        return url_for(url, participant_id=self.id, meeting_id=self.meeting.id)

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
        from mrt.forms.meetings import DefaultParticipantDummyForm
        from mrt.forms.meetings import DefaultMediaParticipantDummyForm
        from mrt.forms.meetings import add_custom_fields_for_meeting
        form_class = {
            Participant.PARTICIPANT: DefaultParticipantDummyForm,
            Participant.MEDIA: DefaultMediaParticipantDummyForm,
        }.get(self.participant_type.code, DefaultParticipantDummyForm)

        nr_fields = len(list(form_class()))
        count = (
            CustomField.query.filter_by(meeting=self.default_meeting)
            .filter_by(is_primary=True)
        ).count()
        if not nr_fields == count:
            add_custom_fields_for_meeting(
                self.default_meeting,
                form_class=form_class)

    def clone(self):
        self.default_meeting = Meeting.get_default()
        participant = copy_attributes(
            Participant(), self, exclude_fk=False,
            exclude=self.EXCLUDE_WHEN_COPYING)
        participant.meeting = self.default_meeting
        participant.participant_type = {
            Participant.PARTICIPANT: Participant.DEFAULT,
            Participant.MEDIA: Participant.DEFAULT_MEDIA,
        }.get(self.participant_type.code, Participant.DEFAULT)
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
        participant = copy_attributes(self, source, exclude_fk=False,
                                      exclude=self.EXCLUDE_WHEN_COPYING)
        for cfv in source.custom_field_values.all():
            cf_clone = self._clone_custom_field(cfv.custom_field)
            db.session.flush()
            self._clone_custom_field_value(participant, cf_clone, cfv)
        return participant


class CustomField(db.Model):

    TEXT = 'text'
    TEXT_AREA = 'text_area'
    IMAGE = 'image'
    EMAIL = 'email'
    CHECKBOX = 'checkbox'
    SELECT = 'select'
    COUNTRY = 'country'
    CATEGORY = 'category'
    EVENT = 'event'

    CUSTOM_FIELDS = (
        (TEXT, 'Text Field'),
        (TEXT_AREA, 'TextArea Field'),
        (IMAGE, 'Image Field'),
        (EMAIL, 'Email Field'),
        (CHECKBOX, 'Checkbox Field'),
        (SELECT, 'Select Field'),
        (COUNTRY, 'Country Field'),
        (CATEGORY, 'Category Field'),
        (EVENT, 'Event Field'),
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

    label = db.relationship('Translation', cascade='all, delete')

    description = db.Column(db.String(512), info={'label': 'Hint'})

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

    value = db.Column(db.String(512), nullable=False)

    choice_id = db.Column(
        db.Integer, db.ForeignKey('custom_field_choice.id'))
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


class Meeting(db.Model):

    query_class = MeetingQuery

    id = db.Column(db.Integer, primary_key=True)

    title_id = db.Column(db.Integer, db.ForeignKey('translation.id'),
                         nullable=False)

    title = db.relationship('Translation', foreign_keys=title_id,
                            cascade='all, delete')

    badge_header_id = db.Column(db.Integer, db.ForeignKey('translation.id'))

    badge_header = db.relationship('Translation', foreign_keys=badge_header_id,
                                   cascade='all, delete')

    acronym = db.Column(db.String(16), nullable=False, unique=True,
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

    venue_city = db.relationship('Translation', foreign_keys=venue_city_id,
                                 cascade='all, delete')

    venue_country = db.Column(CountryType, nullable=False,
                              info={'label': 'Country'})

    owner_id = db.Column(db.Integer, db.ForeignKey('staff.id'))

    owner = db.relationship('Staff', foreign_keys=owner_id)

    online_registration = db.Column(
        db.Boolean, nullable=False, default=True,
        info={'label': 'Allow Online Registration'})

    settings = db.Column(JSONEncodedDict)

    photo_field_id = db.Column(
        db.Integer, db.ForeignKey('custom_field.id',
                                  ondelete="SET NULL",
                                  use_alter=True,
                                  name='fk_photo_field'),)

    photo_field = db.relationship('CustomField',
                                  foreign_keys=photo_field_id,
                                  post_update=True)

    media_photo_field_id = db.Column(
        db.Integer, db.ForeignKey('custom_field.id',
                                  ondelete="SET NULL",
                                  use_alter=True,
                                  name='fk_media_photo_field'),)

    media_photo_field = db.relationship('CustomField',
                                        foreign_keys=media_photo_field_id,
                                        post_update=True)

    def get_absolute_url(self):
        return url_for('meetings.participants', meeting_id=self.id)

    @property
    def media_participant_enabled(self):
        return bool(self.settings and
                    self.settings.get('media_participant_enabled', False))

    @classmethod
    def get_default(cls):
        return cls.query.filter_by(
            meeting_type=MeetingType.query.default()).one()

    def __repr__(self):
        return self.title.english


class CategoryMixin(object):

    PARTICIPANT = 'participant'
    MEDIA = 'media'
    CATEGORY_TYPES = (
        (PARTICIPANT, 'Category for participants'),
        (MEDIA, 'Category for media participants'),
    )

    COUNTRY = 'country'
    ORGANIZATION = 'organization'
    CATEGORY_GROUPS = (
        (COUNTRY, 'Group category by country'),
        (ORGANIZATION, 'Group category by organization'),
    )

    id = db.Column(db.Integer, primary_key=True)

    @declared_attr
    def title_id(cls):
        return db.Column(db.Integer, db.ForeignKey('translation.id'),
                         nullable=False)

    @declared_attr
    def title(cls):
        return db.relationship('Translation', cascade='all, delete')

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

    @classmethod
    def get_categories_for_meeting(cls, category_type=None):
        return (
            cls.query.filter_by(meeting=g.meeting)
            .filter_by(category_type=category_type or cls.PARTICIPANT)
            .order_by(cls.group, cls.sort))


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

    def __init__(self, english=None, french=None, spanish=None):
        self.english = english
        self.french = french
        self.spanish = spanish


class PhraseMixin(object):

    ACK_EMAIL = 'Acknowledge email'
    SUBJECT = 'Subject'
    BODY = 'Body'
    ONLINE_CONFIRMATION = 'Online registration confirmation'
    EMAIL_CONFIRMATION = 'Email registration confirmation'
    PARTICIPANT = 'for participants'
    MEDIA = 'for media'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False)

    @declared_attr
    def description_id(cls):
        return db.Column(db.Integer, db.ForeignKey('translation.id'))

    @declared_attr
    def description(cls):
        return db.relationship('Translation', cascade='all, delete')

    group = db.Column(db.String(32))
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


association_table = db.Table(
    'meeting_type_default_category',
    db.Column('meeting_type_slug',
              db.String(16),
              db.ForeignKey('meeting_type.slug')),
    db.Column('category_default_id',
              db.Integer,
              db.ForeignKey('category_default.id'))
)


fields_association_table = db.Table(
    'meeting_type_custom_field',
    db.Column('meeting_type_slug',
              db.String(16),
              db.ForeignKey('meeting_type.slug')),
    db.Column('custom_field_id',
              db.Integer,
              db.ForeignKey('custom_field.id'))
)


class MeetingType(db.Model):

    __tablename__ = 'meeting_type'

    query_class = MeetingTypeQuery

    slug = db.Column(db.String(16), primary_key=True, info={'label': 'Slug'})
    label = db.Column(db.String(128), nullable=False, info={'label': 'Label'})
    default = db.Column(db.Boolean, nullable=False, default=False)

    default_categories = db.relationship(
        'CategoryDefault', secondary=association_table, backref=db.backref(
            'meeting_types'))

    default_fields = db.relationship(
        'CustomField', secondary=fields_association_table, backref=db.backref(
            'meeting_types'))

    def load_default_phrases(self):
        with open(app.config['DEFAULT_PHRASES_PATH'], 'r') as f:
            default_phrases = json.load(f)
        self.default_phrases += [PhraseDefault(**d) for d in default_phrases]

    def __repr__(self):
        return self.label


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

    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'))
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
                              backref=db.backref('jobs', cascade='delete'))
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


class Rule(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False,
                     info={'label': 'Rule name'})
    meeting_id = db.Column(db.Integer, db.ForeignKey('meeting.id'))
    meeting = db.relationship(
        'Meeting',
        backref=db.backref('rules', cascade='delete'))

    @classmethod
    def get_rules_for_fields(cls, fields=[]):
        ids = [f.id for f in fields]
        return (
            cls.query.filter_by(meeting=g.meeting).filter(
                Action.field.has(CustomField.id.in_(ids)),
                Condition.field.has(CustomField.id.in_(ids)))
        )


class Condition(db.Model):

    __table_args__ = (db.UniqueConstraint('field_id', 'rule_id'),)

    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('rule.id'))
    rule = db.relationship(
        'Rule',
        backref=db.backref('conditions', lazy='dynamic', cascade='delete'))

    field_id = db.Column(db.Integer, db.ForeignKey('custom_field.id'))
    field = db.relationship(
        'CustomField',
        backref=db.backref('conditions', lazy='dynamic'))


class ConditionValue(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    condition_id = db.Column(
        db.Integer,
        db.ForeignKey('condition.id', onupdate="CASCADE", ondelete="CASCADE")
    )
    condition = db.relationship(
        'Condition',
        backref=db.backref('values', lazy='dynamic', cascade='delete'))
    value = db.Column(db.String(255), nullable=False)


class Action(db.Model):

    __table_args__ = (db.UniqueConstraint('field_id', 'rule_id'),)

    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('rule.id'))
    rule = db.relationship(
        'Rule',
        backref=db.backref('actions', lazy='dynamic', cascade='delete'))
    is_visible = db.Column(db.Boolean, default=False)
    is_required = db.Column(db.Boolean, default=False)
    field_id = db.Column(db.Integer, db.ForeignKey('custom_field.id'))
    field = db.relationship(
        'CustomField',
        backref=db.backref('actions', lazy='dynamic'))


def get_or_create_role(name):
    role = Role.query.filter_by(name=name).first()
    if not role:
        role = Role(name=name, permissions=[p[0] for p in PERMISSIONS])
        db.session.add(role)
    return role


def search_for_participant(search, queryset=None):
    queryset = queryset or Participant.query.current_meeting().participants()
    if not isinstance(search, basestring):
        search = str(search)
    search = '{}{}{}'.format('%', search, '%')
    return queryset.filter(
        (cast(Participant.id, String) == search) |
        Participant.first_name.ilike(search) |
        Participant.last_name.ilike(search) |
        Participant.email.ilike(search) |
        Participant.category.has(
            Category.title.has(Translation.english.ilike(search))
        )
    )


def get_participants_full(meeting_id):
    qs = (
        Participant.query
        .outerjoin(Participant.custom_field_values,
                   CustomFieldValue.custom_field)
        .with_entities(Participant, CustomField.slug, CustomFieldValue.value)
        .current_meeting()
        .participants()
        .order_by(Participant.id.desc())
    )

    last_participant = None
    for participant, slug, value in qs:
        if last_participant and participant.id != last_participant.id:
            yield last_participant
            last_participant = None
        last_participant = last_participant or participant
        if slug:
            setattr(last_participant, slug, value)
    if last_participant:
        yield last_participant
