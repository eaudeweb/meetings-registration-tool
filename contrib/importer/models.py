from datetime import datetime
from urllib import urlretrieve
from flask import current_app as app

from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import mapper, sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy_utils import Country

from mrt import models
from mrt.models import db
from mrt.forms.meetings import add_custom_fields_for_meeting
from mrt.utils import copy_attributes

from contrib.importer.definitions import COLORS, DEFAULT_COLOR
from contrib.importer.definitions import LANGUAGES, REGIONS, CUSTOM_FIELDS
from contrib.importer.definitions import REPRESENTING_TEMPLATES


class Meeting(object):
    pass


class Participant(object):

    TITLE_MAPPING = {
        'Mr': 'Mr',
        'Ms': 'Ms',
        'M': 'Mr',
        'Sra.': 'Ms',
        'Sr.': 'Mr',
        'Mme.': 'Ms',
        '': 'Mr'
    }

    def __repr__(self):
        return str(self.id)


class ParticipantMeeting(object):
    pass


class Category(object):

    def __repr__(self):
        return self.data['name_E']


class CategoryMeeting(object):
    pass


class Event(object):
    pass


class ParticipantEvent(object):
    pass


class Phrase(object):
    pass


def session(uri):
    engine = create_engine(uri)
    meta = MetaData(engine)
    meeting = Table('meeting', meta, autoload=True)
    participant = Table('person', meta, autoload=True)
    participant_meeting = Table('personmeeting', meta, autoload=True)
    category = Table('category', meta, autoload=True)
    category_meeting = Table('categorymeeting', meta, autoload=True)
    event = Table('event', meta, autoload=True)
    participant_event = Table('personevent', meta, autoload=True)
    phrase = Table('phrase', meta, autoload=True)
    mapper(Meeting, meeting)
    mapper(Participant, participant)
    mapper(ParticipantMeeting, participant_meeting)
    mapper(Category, category)
    mapper(CategoryMeeting, category_meeting)
    mapper(Event, event)
    mapper(ParticipantEvent, participant_event)
    mapper(Phrase, phrase)
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
        meeting_type.load_default_phrases()
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
            models.Category.title.has(english=category.data['name_E']),
            models.Category.meeting == migrated_meeting,
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


def migrate_phrase(phrase, migrated_meeting):
    online_registration = 'Online registration'
    confirmation = 'Confirmation '
    migrated_phrase = models.Phrase()

    description = models.Translation(english=phrase.data['description_E'],
                                     french=phrase.data['description_F'],
                                     spanish=phrase.data['description_S'])
    db.session.add(description)
    db.session.flush()
    migrated_phrase.description = description

    migrated_phrase.name = phrase.data['label']
    if online_registration in phrase.data['group']:
        migrated_phrase.group = online_registration
        migrated_phrase.name = confirmation + migrated_phrase.name
    else:
        migrated_phrase.group = phrase.data['group']
    migrated_phrase.sort = phrase.data['sort']

    migrated_phrase.meeting = migrated_meeting

    db.session.add(migrated_phrase)
    db.session.commit()


def copy_missing_phrases(default_phrases, migrated_meeting):
    last_sort = max([x.sort for x in migrated_meeting.phrases.all()])
    for phrase in default_phrases:
        if not migrated_meeting.phrases.filter_by(name=phrase.name,
                                                  group=phrase.group).first():
            new_phrase = copy_attributes(models.Phrase(), phrase)
            new_phrase.description = (
                copy_attributes(models.Translation(), phrase.description)
                if phrase.description else models.Translation(english=''))
            new_phrase.meeting = migrated_meeting
            new_phrase.sort = last_sort + 1
            db.session.add(new_phrase)
            last_sort += 1
    db.session.commit()


def migrate_participant(participant, participant_meeting, migrated_category,
                        migrated_meeting, custom_fields, photo_field):
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
    migrated_participant.title = Participant.TITLE_MAPPING[
        participant.data['personal_name_title']]
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

    for key, custom_field in custom_fields.iteritems():
        create_custom_field_value(migrated_participant, custom_field,
                                  participant.data[key])

    photo = participant.data.get('photo')
    if photo_field and photo:
        create_custom_field_value(migrated_participant, photo_field, photo)
        urlretrieve(app.config['PHOTOS_BASE_URL'] + photo,
                    app.config['UPLOADED_CUSTOM_DEST'] / photo)

    return migrated_participant


def migrate_event(event, migrated_meeting):
    migrated_event = models.CustomField()

    date = event.data['date']
    date_end = event.data.get('date_end', None)
    if date_end and date_end != date:
        date += u' - {}'.format(date_end)

    def add_date(label):
        return u'{}, {}'.format(label, date)

    label = models.Translation(english=add_date(event.data['description_E']),
                               french=add_date(event.data['description_F']),
                               spanish=add_date(event.data['description_S']))
    db.session.add(label)
    db.session.flush()
    migrated_event.label = label

    migrated_event.description = event.data['venue']
    migrated_event.field_type = models.CustomField.EVENT
    migrated_event.custom_field_type = models.CustomField.PARTICIPANT
    migrated_event.visible_on_registration_form = True

    migrated_event.meeting = migrated_meeting

    db.session.add(migrated_event)
    db.session.commit()

    return migrated_event


def create_custom_field(migrated_meeting, **kwargs):
    label = models.Translation(**kwargs.pop('label'))
    db.session.add(label)
    db.session.flush()

    custom_field = models.CustomField(**kwargs)
    custom_field.label = label
    custom_field.meeting = migrated_meeting

    db.session.add(custom_field)
    db.session.commit()

    return custom_field


def create_custom_field_value(migrated_participant, migrated_custom_field,
                              value):
    migrated_cfv = models.CustomFieldValue()

    migrated_cfv.custom_field = migrated_custom_field
    migrated_cfv.participant = migrated_participant
    migrated_cfv.value = value

    db.session.add(migrated_cfv)
    db.session.commit()


def create_custom_fields(migrated_meeting):
    custom_fields = {}
    for participant_field, label in CUSTOM_FIELDS.iteritems():
        custom_fields[participant_field] = create_custom_field(
            migrated_meeting,
            label={'english': label},
            field_type=models.CustomField.TEXT,
            visible_on_registration_form=True,
            custom_field_type=models.CustomField.PARTICIPANT)
    return custom_fields


def create_photo_field(migrated_meeting):
    return create_custom_field(
        migrated_meeting,
        label={'english': u'Photo'},
        field_type=models.CustomField.IMAGE,
        visible_on_registration_form=True,
        custom_field_type=models.CustomField.PARTICIPANT)
