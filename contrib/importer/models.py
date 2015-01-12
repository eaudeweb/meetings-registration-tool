from datetime import datetime

from mrt import models
from mrt.models import db
from mrt.forms.meetings import add_custom_fields_for_meeting
from mrt.utils import copy_attributes

from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import mapper, sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy_utils import Country

from contrib.importer.definitions import COLORS, DEFAULT_COLOR
from contrib.importer.definitions import LANGUAGES, REGIONS
from contrib.importer.definitions import REPRESENTING_TEMPLATES


class Meeting(object):
    pass


class Participant(object):

    def __repr__(self):
        return str(self.id)


class ParticipantMeeting(object):
    pass


class Category(object):

    def __repr__(self):
        return self.data['name_E']


class CategoryMeeting(object):
    pass


def session(uri):
    engine = create_engine(uri)
    meta = MetaData(engine)
    meeting = Table('meeting', meta, autoload=True)
    participant = Table('person', meta, autoload=True)
    participant_meeting = Table('personmeeting', meta, autoload=True)
    category = Table('category', meta, autoload=True)
    category_meeting = Table('categorymeeting', meta, autoload=True)
    mapper(Meeting, meeting)
    mapper(Participant, participant)
    mapper(ParticipantMeeting, participant_meeting)
    mapper(Category, category)
    mapper(CategoryMeeting, category_meeting)
    return sessionmaker(bind=engine)()


def migrate_meeting(meeting):
    migrated_meeting = models.Meeting()
    title = models.Translation(english=meeting.data['info_description_E'],
                               french=meeting.data['info_description_F'],
                               spanish=meeting.data['info_description_S'])
    db.session.add(title)
    db.session.flush()
    migrated_meeting.title = title

    badge_header = models.Translation(
        english=meeting.data['info_badge_header_E'],
        french=meeting.data['info_badge_header_F'],
        spanish=meeting.data['info_badge_header_S'])
    db.session.add(badge_header)
    db.session.flush()
    migrated_meeting.badge_header = badge_header

    migrated_meeting.acronym = meeting.data['info_acronym']

    try:
        meeting_type = models.MeetingType.query.filter_by(
            slug=meeting.data['info_type']).one()
    except NoResultFound:
        meeting_type = models.MeetingType(slug=meeting.data['info_type'],
                                          label=meeting.data['info_type'])
        db.session.add(meeting_type)
        db.session.flush()
    migrated_meeting.meeting_type = meeting_type

    date_start = datetime.strptime(meeting.data['info_date_start'],
                                   '%Y-%m-%d').date()
    date_end = datetime.strptime(meeting.data['info_date_end'],
                                 '%Y-%m-%d').date()
    migrated_meeting.date_start = date_start
    migrated_meeting.date_end = date_end

    city = models.Translation(english=meeting.data['info_venue_city_E'],
                              french=meeting.data['info_venue_city_F'],
                              spanish=meeting.data['info_venue_city_S'])

    migrated_meeting.venue_address = meeting.data['info_venue_address']
    migrated_meeting.venue_city = city
    migrated_meeting.venue_country = meeting.data['info_venue_country']
    migrated_meeting.online_registration = (
        True if meeting.data['info_online_registration'] == 'allowed'
        else False)

    db.session.add(migrated_meeting)
    add_custom_fields_for_meeting(migrated_meeting)
    db.session.commit()
    return migrated_meeting


def migrate_category(category_and_category_meeting, migrated_meeting):
    category, category_meeting = category_and_category_meeting
    try:
        migrated_category = models.Category.query.filter(
            models.Category.title.has(english=category.data['name_E'])
        ).one()
        return migrated_category
    except NoResultFound:
        pass

    migrated_category = models.Category()
    title = models.Translation(english=category.data['name_E'],
                               french=category.data['name_F'],
                               spanish=category.data['name_S'])
    db.session.add(title)
    db.session.flush()
    migrated_category.title = title

    color = COLORS.get(category.data['badge_color'], DEFAULT_COLOR)
    migrated_category.color = color

    representing = REPRESENTING_TEMPLATES.get(category.data['templates_list'])
    if representing:
        migrated_category.representing = representing

    if category.data['stat'] == 'Media':
        category_type = models.Category.MEDIA
    else:
        category_type = models.Category.PARTICIPANT

    migrated_category.category_type = category_type

    form_type = category_meeting.form_type
    if form_type == 'media':
        migrated_category.group = models.Category.ORGANIZATION
    else:
        migrated_category.group = models.Category.COUNTRY

    try:
        sort = int(category.data['form_sort'])
    except (TypeError, ValueError):
        sort = None
    migrated_category.sort = sort

    if form_type:
        migrated_category.visible_on_registration_form = True
    else:
        migrated_category.visible_on_registration_form = False

    migrated_category.meeting = migrated_meeting

    db.session.add(migrated_category)

    try:
        models.CategoryDefault.query.filter(
            models.CategoryDefault.title.has(english=category.data['name_E'])
        ).one()
    except NoResultFound:
        migrated_category_default = copy_attributes(models.CategoryDefault(),
                                                    migrated_category)
        title = models.Translation(english=category.data['name_E'],
                                   french=category.data['name_F'],
                                   spanish=category.data['name_S'])
        db.session.add(title)
        db.session.flush()
        migrated_category_default.title = title
        db.session.add(migrated_category_default)

    db.session.commit()
    return migrated_category


def migrate_participant(participant, participant_meeting, migrated_category,
                        migrated_meeting):
    try:
        models.Participant.query.filter_by(
            first_name=participant.data['personal_first_name'],
            last_name=participant.data['personal_last_name'],
            email=participant.data['personal_email'],
            meeting=migrated_meeting).one()
        return
    except NoResultFound:
        pass

    migrated_participant = models.Participant()
    migrated_participant.title = participant.data['personal_name_title']
    migrated_participant.first_name = participant.data['personal_first_name']
    migrated_participant.last_name = participant.data['personal_last_name']
    migrated_participant.email = participant.data['personal_email']

    migrated_participant.category = migrated_category

    lang = LANGUAGES[participant.data['personal_language']]
    migrated_participant.language = lang

    country_iso = participant.data['personal_country']
    if country_iso:
        migrated_participant.country = Country(country_iso)

    represented_country_iso = participant.data['representing_country']
    if represented_country_iso:
        migrated_participant.represented_country = \
            Country(represented_country_iso)

    region = REGIONS.get(participant.data['representing_region'])
    if region:
        migrate_participant.represented_region = region

    represented_org = participant.data['representing_organization']
    migrate_participant.represented_organization = represented_org

    migrated_participant.participant_type = models.Participant.PARTICIPANT

    attended = participant_meeting.data['meeting_flags_attended']
    verified = participant_meeting.data['meeting_flags_verified']
    credentials = participant_meeting.data['meeting_flags_credentials']
    migrated_participant.attended = attended or False
    migrated_participant.verified = verified or False
    migrated_participant.credentials = credentials or False

    migrated_participant.meeting = migrated_meeting

    db.session.add(migrated_participant)
    db.session.commit()
