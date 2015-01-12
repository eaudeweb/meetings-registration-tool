import click
from contrib.importer import models


@click.group()
def cli():
    pass


@cli.command(name='import')
@click.argument('database')
@click.argument('meeting_id')
@click.pass_context
def import_(ctx, database, meeting_id):
    app = ctx.obj['app']
    with app.test_request_context():
        uri_from_config = ctx.obj['app'].config['SQLALCHEMY_DATABASE_URI']
        uri = '%s/%s' % (uri_from_config.rsplit('/', 1)[0], database)
        ses = models.session(uri)
        meeting = ses.query(models.Meeting).get(meeting_id)
        participants_meeting = (
            ses.query(models.Participant)
            .join(models.ParticipantMeeting)
            .with_entities(models.Participant, models.ParticipantMeeting)
            .filter(models.ParticipantMeeting.meeting_id == meeting.id)
        )

        migrated_meeting = models.migrate_meeting(meeting)

        for participant, participant_meeting in participants_meeting.all():
            category_id = participant_meeting.category
            category_meeting = (
                ses.query(models.Category, models.CategoryMeeting)
                .join(models.CategoryMeeting)
                .filter(models.Category.data['id'] == str(category_id))
                .first()
            )
            migrated_category = models.migrate_category(category_meeting,
                                                        migrated_meeting)
            models.migrate_participant(participant,
                                       participant_meeting,
                                       migrated_category,
                                       migrated_meeting)

            click.echo('Participant %r in category %r processed' %
                       (participant, category_meeting[0]))

        click.echo('Total participants processed %d' %
                   participants_meeting.count())
