from factory.alchemy import SQLAlchemyModelFactory as BaseModelFactory
from factory import SubFactory, SelfAttribute
from sqlalchemy_utils import CountryType, Choice
from werkzeug.security import generate_password_hash

from mrt import models

from datetime import date


class SQLAlchemyModelFactory(BaseModelFactory):

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        obj = super(SQLAlchemyModelFactory, cls)._create(
            model_class, *args, **kwargs)
        session = cls._meta.sqlalchemy_session
        session.commit()
        return obj


class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.User
        sqlalchemy_session = models.db.session

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        obj = super(SQLAlchemyModelFactory, cls)._create(
            model_class, *args, **kwargs)
        session = cls._meta.sqlalchemy_session
        obj.password = generate_password_hash(obj.password)
        session.commit()
        return obj

    email = 'johndoe@eaudeweb.ro'
    password = 'eaudeweb'


class MeetingTitleFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.Translation
        sqlalchemy_session = models.db.session

    english = 'Twenty-first meeting of the Plants Committee'


class MeetingVenueCityFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.Translation
        sqlalchemy_session = models.db.session

    english = 'Bucharest'


class CountryTypeFactory(SQLAlchemyModelFactory):
    class Meta:
        model = CountryType
        sqlalchemy_session = models.db.session


class BadgeHaderFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.Translation
        sqlalchemy_session = models.db.session

    english = 'Meeting Badge Header'


class MeetingFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.Meeting
        sqlalchemy_session = models.db.session

    title = SubFactory(MeetingTitleFactory)
    badge_header = SubFactory(BadgeHaderFactory)
    acronym = 'MOTPC'
    meeting_type = 'cop'
    date_start = date.today()
    date_end = date.today()
    venue_city = SubFactory(MeetingVenueCityFactory)
    venue_country = 'RO'
    online_registration = False


class RoleFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.Role
        sqlalchemy_session = models.db.session

    name = 'MeetingsAdmin'
    permissions = ('manage_meeting', 'manage_participant', 'manage_default',
                   'manage_media_participant', 'view_participant')


class StaffFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.Staff
        sqlalchemy_session = models.db.session

    title = 'Head of department'
    full_name = 'John Doe'
    user = SubFactory(UserFactory)


class CategoryDefaultNameFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.Translation
        sqlalchemy_session = models.db.session

    english = 'Member of Party'


class CategoryDefaultFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.CategoryDefault
        sqlalchemy_session = models.db.session

    title = SubFactory(CategoryDefaultNameFactory)
    color = '#93284c'
    type = Choice(code='member', value='Member')


class MeetingCategoryFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.Category
        sqlalchemy_session = models.db.session

    title = SubFactory(CategoryDefaultNameFactory)
    color = '#93284c'
    type = Choice(code='member', value='Member')
    meeting = SubFactory(MeetingFactory)
    representing = 'region.html'


class PhraseDescriptionFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.Translation
        sqlalchemy_session = models.db.session

    english = 'Email body'


class PhraseDefaultFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.PhraseDefault
        sqlalchemy_session = models.db.session

    name = 'Credentials'
    group = 'Acknowledge details'
    meeting_type = 'cop'
    description = SubFactory(PhraseDescriptionFactory)


class PhraseMeetingFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.Phrase
        sqlalchemy_session = models.db.session

    name = 'Credentials'
    group = 'Acknowledge details'
    description = SubFactory(PhraseDescriptionFactory)
    meeting = SubFactory(MeetingFactory)


class RoleUserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.RoleUser
        sqlalchemy_session = models.db.session

    role = SubFactory(RoleFactory)
    user = SubFactory(UserFactory)


class RoleUserMeetingFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.RoleUser
        sqlalchemy_session = models.db.session

    role = SubFactory(RoleFactory)
    user = SubFactory(UserFactory)
    meeting = SubFactory(MeetingFactory)


class ParticipantFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.Participant
        sqlalchemy_session = models.db.session

    category = SubFactory(MeetingCategoryFactory)
    meeting = SelfAttribute('category.meeting')
    title = 'Mr'
    first_name = 'John'
    last_name = 'Doe'
    email = 'john@doe.com'
    language = 'en'
    country = 'FR'
    represented_region = 'asia'


class MailLogFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.MailLog
        sqlalchemy_session = models.db.session

    to = SubFactory(ParticipantFactory)
    meeting = SelfAttribute('to.meeting')
    subject = 'Test subject'
    message = 'Test message'


class MediaParticipantFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.MediaParticipant
        sqlalchemy_session = models.db.session

    category = SubFactory(MeetingCategoryFactory)
    meeting = SelfAttribute('category.meeting')
    title = 'Ms'
    first_name = 'Jane'
    last_name = 'Doe'
    email = 'jane@doe.com'


class CustomFieldLabelFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.Translation
        sqlalchemy_session = models.db.session

    english = 'picture'


class CustomFieldFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.CustomField
        sqlalchemy_session = models.db.session

    label = SubFactory(CustomFieldLabelFactory)
    meeting = SubFactory(MeetingFactory)
    field_type = 'image'
    required = False


class ProfilePictureFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.CustomFieldValue
        sqlalchemy_session = models.db.session
    participant = SubFactory(ParticipantFactory)
    custom_field = SubFactory(CustomFieldFactory,
                              meeting=SelfAttribute('..participant.meeting'))
    value = 'image.png'


class UserNotificationFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.UserNotification
        sqlalchemy_session = models.db.session

    user = SubFactory(UserFactory)
    meeting = SubFactory(MeetingFactory)
    notification_type = 'notify_participant'


def normalize_data(data):

    def convert_data(value):
        if isinstance(value, date):
            return value.strftime('%d.%m.%Y')
        elif isinstance(value, bool):
            return u'y' if value else u''
        elif isinstance(value, Choice):
            return value.code
        return value

    new_data = dict(data)
    for k, v in new_data.items():
        new_data[k] = convert_data(v)

    return new_data
