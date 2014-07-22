from factory.alchemy import SQLAlchemyModelFactory as BaseModelFactory
from factory import SubFactory
from sqlalchemy_utils import CountryType
from werkzeug.security import generate_password_hash

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
        model = Translation
        sqlalchemy_session = db.session

    english = 'Twenty-first meeting of the Plants Committee'


class MeetingVenueCityFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Translation
        sqlalchemy_session = db.session

    english = 'Bucharest'


class CountryTypeFactory(SQLAlchemyModelFactory):
    class Meta:
        model = CountryType
        sqlalchemy_session = db.session


class MeetingFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Meeting
        sqlalchemy_session = db.session

    title = SubFactory(MeetingTitleFactory)
    acronym = 'MOTPC'
    meeting_type = 'cop'
    date_start = date.today()
    date_end = date.today()
    venue_city = SubFactory(MeetingVenueCityFactory)
    venue_country = 'RO'
    online_registration = False
