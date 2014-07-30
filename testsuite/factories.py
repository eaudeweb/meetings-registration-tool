from factory.alchemy import SQLAlchemyModelFactory as BaseModelFactory
from factory import SubFactory
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


class MeetingFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.Meeting
        sqlalchemy_session = models.db.session

    title = SubFactory(MeetingTitleFactory)
    acronym = 'MOTPC'
    meeting_type = 'cop'
    date_start = date.today()
    date_end = date.today()
    venue_city = SubFactory(MeetingVenueCityFactory)
    venue_country = 'RO'
    online_registration = False


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

    name = SubFactory(CategoryDefaultNameFactory)
    color = '#93284c'
    type = Choice(code='member', value='Member')


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
