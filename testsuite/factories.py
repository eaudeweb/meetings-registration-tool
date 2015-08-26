from factory.alchemy import SQLAlchemyModelFactory as BaseModelFactory
from factory import SubFactory, SelfAttribute, Sequence
from factory import post_generation, sequence
from sqlalchemy_utils import CountryType, Choice
from werkzeug.security import generate_password_hash

from mrt import models
from mrt.definitions import MEETING_TYPES

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

    email = Sequence(lambda n: 'john%d@doe.com' % n)
    password = 'eaudeweb'
    is_superuser = False


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


class MeetingTypeFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.MeetingType
        sqlalchemy_session = models.db.session

    label = 'Conference of the Parties'

    @sequence
    def slug(n):
        return MEETING_TYPES[n - 1][0] if n <= len(MEETING_TYPES) else str(n)


class MeetingFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.Meeting
        sqlalchemy_session = models.db.session

    title = SubFactory(MeetingTitleFactory)
    badge_header = SubFactory(BadgeHaderFactory)
    venue_address = 'Main Street, Nr. 7'
    acronym = Sequence(lambda n: 'MOTPC{}'.format(n))
    meeting_type = SubFactory(MeetingTypeFactory)
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
    permissions = ('manage_meeting', 'manage_participant',
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


class MeetingCategoryFactory(SQLAlchemyModelFactory):

    class Meta:
        model = models.Category
        sqlalchemy_session = models.db.session

    title = SubFactory(CategoryDefaultNameFactory)
    color = '#93284c'
    meeting = SubFactory(MeetingFactory)
    representing = 'region.html'
    group = 'country'
    visible_on_registration_form = True
    category_type = models.Category.PARTICIPANT


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
    meeting_type = SubFactory(MeetingTypeFactory)
    description = SubFactory(PhraseDescriptionFactory)


class PhraseMeetingFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.Phrase
        sqlalchemy_session = models.db.session

    name = 'Credentials'
    group = 'Acknowledge details'
    description = SubFactory(PhraseDescriptionFactory)
    meeting = SubFactory(MeetingFactory)


class RoleUserMeetingFactory(SQLAlchemyModelFactory):

    class Meta:
        model = models.RoleUser
        sqlalchemy_session = models.db.session

    role = SubFactory(RoleFactory)
    user = SubFactory(UserFactory)
    meeting = SubFactory(MeetingFactory)

    @post_generation
    def staff(self, create, extracted, **kwargs):
        if not create:
            return
        staff = extracted or StaffFactory(user=self.user)
        return staff


class ParticipantFactory(SQLAlchemyModelFactory):

    class Meta:
        model = models.Participant
        sqlalchemy_session = models.db.session

    category = SubFactory(MeetingCategoryFactory)
    meeting = SelfAttribute('category.meeting')
    title = 'Mr'
    first_name = 'John'
    last_name = 'Doe'
    email = Sequence(lambda n: 'john%d@doe.com' % n)
    language = 'English'
    country = 'FR'
    represented_region = 'Asia'

    @post_generation
    def representing(self, create, extracted, **kwargs):
        self.set_representing()


class ParticipantUserFactory(ParticipantFactory):

    user = SubFactory(UserFactory)


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
        model = models.Participant
        sqlalchemy_session = models.db.session

    category = SubFactory(MeetingCategoryFactory)
    meeting = SelfAttribute('category.meeting')
    title = 'Ms'
    first_name = 'Jane'
    last_name = 'Doe'
    email = 'jane@doe.com'
    country = 'BR'
    participant_type = models.Participant.MEDIA


class CustomFieldLabelFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.Translation
        sqlalchemy_session = models.db.session

    english = 'picture'


class CustomFieldHintFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.Translation
        sqlalchemy_session = models.db.session

    english = 'hint'


class CustomFieldFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.CustomField
        sqlalchemy_session = models.db.session

    label = SubFactory(CustomFieldLabelFactory)
    hint = SubFactory(CustomFieldHintFactory)
    meeting = SubFactory(MeetingFactory)
    field_type = 'image'
    required = True
    visible_on_registration_form = True
    custom_field_type = models.CustomField.PARTICIPANT


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


class RuleFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.Rule
        sqlalchemy_session = models.db.session

    name = Sequence(lambda n: 'Rule %d' % n)
    meeting = SubFactory(MeetingFactory, online_registration=True)


class ConditionFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.Condition
        sqlalchemy_session = models.db.session

    rule = SubFactory(RuleFactory)
    field = SubFactory(CustomFieldFactory,
                       meeting=SelfAttribute('..rule.meeting'),
                       field_type='country')


class ConditionValueFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.ConditionValue
        sqlalchemy_session = models.db.session

    condition = SubFactory(ConditionFactory)
    value = 'RO'


class ActionFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.Action
        sqlalchemy_session = models.db.session

    rule = SubFactory(RuleFactory)
    field = SubFactory(CustomFieldFactory,
                       meeting=SelfAttribute('..rule.meeting'),
                       field_type='country')
    is_visible = False
    is_required = False


class EventFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.CustomField
        sqlalchemy_session = models.db.session

    label = SubFactory(CustomFieldLabelFactory)
    meeting = SubFactory(MeetingFactory)
    field_type = models.CustomField.EVENT
    required = False
    visible_on_registration_form = False
    custom_field_type = models.CustomField.PARTICIPANT


class DocumentFieldFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.CustomField
        sqlalchemy_session = models.db.session

    label = SubFactory(CustomFieldLabelFactory)
    meeting = SubFactory(MeetingFactory)
    field_type = models.CustomField.DOCUMENT
    required = True
    visible_on_registration_form = True
    custom_field_type = models.CustomField.PARTICIPANT


class EventValueFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.CustomFieldValue
        sqlalchemy_session = models.db.session

    custom_field = SubFactory(EventFactory)
    participant = SubFactory(ParticipantFactory)
    value = 'true'


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
