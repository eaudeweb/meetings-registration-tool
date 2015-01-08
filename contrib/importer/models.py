from datetime import datetime
from mrt import models
from mrt.models import db
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import mapper, sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from contrib.importer.definitions import COLORS, DEFAULT_COLOR
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

    db.session.commit()


def migrate_category(category_and_category_meeting):
    category, category_meeting = category_and_category_meeting
    migrated_category = models.Category()
    title = models.Translation(english=meeting.data['name_E'],
                               french=meeting.data['name_F'],
                               spanish=meeting.data['name_S'])
    db.session.add(title)
    db.session.flush()
    migrated_category.title = title

    color = COLORS.get(meeting.data['badge_color'], DEFAULT_COLOR)
    migrated_category.color = color

    representing = REPRESENTING_TEMPLATES.get(meeting.data['templates_list'])
    if not representing:
        click.echo('Value error for %s' % meeting.data['templates_list'])
        raise ValueError()

    if meeting.data['stat'] == 'Media':
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
    except TypeError, ValueError:
        sort = None
    migrated_category.sort = sort

    if form_type:
        migrated_category.visible_on_registration_form = True
    else:
        migrated_category.visible_on_registration_form = False

