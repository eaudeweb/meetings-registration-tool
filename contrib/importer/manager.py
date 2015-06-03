import click
import json
from sqlalchemy.exc import IntegrityError

from contrib.importer.models import (
    Category, CategoryMeeting, Event, Meeting, Participant, ParticipantEvent,
    ParticipantMeeting, Phrase, session,
    create_custom_field_value, create_custom_fields, create_photo_field,
    migrate_category, migrate_event, migrate_meeting, migrate_participant,
    migrate_phrase, copy_missing_phrases
)
from mrt.models import PhraseDefault as PhraseDefault_


@click.group()
def cli():
    pass


@cli.command(name='import')
@click.argument('database')
@click.argument('meeting_id')
@click.option('--with-photos', is_flag=True)
@click.pass_context
def import_(ctx, database, meeting_id, with_photos):
    app = ctx.obj['app']
    with app.test_request_context():
        uri_from_config = ctx.obj['app'].config['SQLALCHEMY_DATABASE_URI']
        uri = '%s/%s' % (uri_from_config.rsplit('/', 1)[0], database)
        ses = session(uri)
        meeting = ses.query(Meeting).get(meeting_id)
        participants = (
            ses.query(Participant)
            .join(ParticipantMeeting)
            .outerjoin(ParticipantEvent)
            .with_entities(Participant, ParticipantMeeting, ParticipantEvent)
            .filter(ParticipantMeeting.meeting_id == meeting.id)
        )

        try:
            migrated_meeting = migrate_meeting(meeting)
        except IntegrityError:
            click.echo('Another meeting with this acronym exists')
            ctx.exit()

        photo_field = (create_photo_field(migrated_meeting)
                       if with_photos else None)

        custom_fields = create_custom_fields(migrated_meeting)

        events = ses.query(Event).filter(Event.meeting_id == meeting.id)
        migrated_events = {}
        for event in events.all():
            migrated_events[event.id] = migrate_event(event, migrated_meeting)

        phrases = ses.query(Phrase).filter(Phrase.meeting_id == meeting.id)
        for phrase in phrases.all():
            migrate_phrase(phrase, migrated_meeting)
        with open(ctx.obj['app'].config['DEFAULT_PHRASES_PATH'], 'r') as f:
            default_phrases = json.load(f)
        default_phrases = [PhraseDefault_(**d) for d in default_phrases]
        copy_missing_phrases(default_phrases, migrated_meeting)

        migrated_participants = {}
        for participant, participant_meeting, participant_event in participants:
            if participant not in migrated_participants:
                category_id = participant_meeting.category
                category_meeting = (
                    ses.query(Category, CategoryMeeting)
                    .join(CategoryMeeting)
                    .filter(Category.data['id'] == str(category_id))
                    .first()
                )
                migrated_category = migrate_category(category_meeting,
                                                     migrated_meeting)
                migrated_participants[participant] = migrate_participant(
                    participant,
                    participant_meeting,
                    migrated_category,
                    migrated_meeting,
                    custom_fields,
                    photo_field)

                click.echo('Participant %r in category %r processed' %
                           (participant, category_meeting[0]))

            if participant_event and migrated_participants.get(participant):
                create_custom_field_value(
                    migrated_participants[participant],
                    migrated_events[participant_event.event_id],
                    'true')

        click.echo('Total participants processed %d' % participants.count())
