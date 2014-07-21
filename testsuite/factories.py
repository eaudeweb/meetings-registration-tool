from factory.alchemy import SQLAlchemyModelFactory as BaseModelFactory
from factory import Sequence, SubFactory
from sqlalchemy_utils import CountryType

from mrt.models import db, User, Meeting, Translation

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
        model = User
        sqlalchemy_session = db.session

    id = Sequence(lambda n: n)
    email = Sequence(lambda n: u'user%d@eaudeweb.ro' % n)


class MeetingTitleFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Translation
        sqlalchemy_session = db.session

    id = Sequence(lambda n: n)
    english = 'Twenty-first meeting of the Plants Committee'


class MeetingVenueCityFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Translation
        sqlalchemy_session = db.session

    id = Sequence(lambda n: n)
    english = 'Bucharest'


class CountryTypeFactory(SQLAlchemyModelFactory):
    class Meta:
        model = CountryType
        sqlalchemy_session = db.session


class MeetingFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Meeting
        sqlalchemy_session = db.session

    id = Sequence(lambda n: n)
    title = SubFactory(MeetingTitleFactory)
    acronym = 'MOTPC'
    meeting_type = 'cop'
    date_start = date.today()
    date_end = date.today()
    venue_city = SubFactory(MeetingVenueCityFactory)
    venue_country = 'RO'
    online_registration = False
