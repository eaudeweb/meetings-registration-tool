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
    uri_from_config = ctx.obj['app'].config['SQLALCHEMY_DATABASE_URI']
    uri = '%s/%s' % (uri_from_config.rsplit('/', 1)[0], database)
    ses = models.session(uri)
    meeting = ses.query(models.Meeting).get(meeting_id)
    participants = (
        ses.query(models.Participant)
        .join(models.ParticipantMeeting)
        .with_entities(models.Participant, models.ParticipantMeeting.category)
        .filter(models.ParticipantMeeting.meeting_id == meeting.id)
    )

    app = ctx.obj['app']
    with app.app_context():
        migrated_meeting = models.migrate_meeting(meeting)

    for participant, category_id in participants.all():
        category_and_category_meeting = (
            ses.query(models.Category, models.CategoryMeeting)
            .join(models.CategoryMeeting)
            .filter(models.Category.data['id'] == str(category_id))
            .first()
        )
        with app.app_context():
            models.migrate_category(category_and_category_meeting,
                                    migrated_meeting)

        click.echo('Participant %r in category %r processed' %
                   (participant, category_and_category_meeting[0]))

    click.echo('Total participants processed %d' % participants.count())

