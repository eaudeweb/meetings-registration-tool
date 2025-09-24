from datetime import datetime
from dateutil.relativedelta import relativedelta
import click
import code
import re
import os
import subprocess
import logging
import json
from sqlalchemy import or_

import requests
from flask import g
from alembic.config import CommandLine
from rq import Queue, Connection, Worker
from rq import get_failed_queue

from mrt.models import CustomFieldValue, redis_store, db
from mrt.models import User, Staff, Job
from mrt.models import CustomField, Translation, Participant, Meeting, MeetingType
from mrt.pdf import _clean_printouts
from mrt.scripts.informea import get_meetings
from mrt.utils import slugify, unlink_participant_custom_file, validate_email
from collections import defaultdict
from mrt.forms.meetings.meeting import _add_choice_values_for_custom_field

logger = logging.getLogger("mrt")


@click.group()
def cli():
    pass


@cli.command()
@click.pass_context
@click.option('-h', '--host', default='127.0.0.1')
@click.option('-p', '--port', default=5000)
def runserver(ctx, host, port):
    app = ctx.obj['app']
    app.run(host, port)


@cli.command()
@click.pass_context
def shell(ctx):
    app = ctx.obj['app']
    context = dict(app=app)
    with app.test_request_context():
        try:
            from bpython import embed
            embed(locals_=context)
            return
        except ImportError:
            pass
        code.interact(local=context)


@cli.command()
@click.pass_context
def create_user(ctx):
    email = click.prompt('Enter email', type=str)
    while not validate_email(email):
        email = click.prompt('Invalid email. Enter another email', type=str)
    password = click.prompt('Enter password', type=str, hide_input=True)
    confirm = click.prompt('Enter password again', type=str, hide_input=True)

    if password == confirm:
        app = ctx.obj['app']
        with app.app_context():
            user = User(email=email)
            user.set_password(password)
            db.session.add(user)
            staff = Staff(user=user, full_name='')
            db.session.add(staff)
            db.session.commit()
            click.echo('User has been created')
    else:
        click.echo('Passwords differ')


@cli.command()
@click.pass_context
@click.option('--email', type=str, default='')
@click.option('--password', type=str, default='')
def create_superuser(ctx, email, password):
    if not email:
        email = click.prompt('Enter email', type=str)
    while not validate_email(email):
        email = click.prompt('Invalid email. Enter another email', type=str)
    if not password:
        password = click.prompt('Enter password', type=str, hide_input=True)
        confirm = click.prompt('Enter password again',
                               type=str, hide_input=True)
    else:
        confirm = password
    if password == confirm:
        app = ctx.obj['app']
        with app.app_context():
            user = User(email=email, is_superuser=True)
            user.set_password(password)
            db.session.add(user)
            staff = Staff(user=user, full_name='')
            db.session.add(staff)
            db.session.commit()
            click.echo('Superuser has been created')
    else:
        click.echo('Passwords differ')


@cli.command()
@click.argument('alembic_args', nargs=-1, type=click.Path())
@click.pass_context
def alembic(ctx, alembic_args):
    app = ctx.obj['app']
    with app.test_request_context():
        CommandLine().main(argv=alembic_args)


@cli.group()
def rq():
    pass


@rq.command()
@click.argument('queues', nargs=-1)
@click.pass_context
def workers(ctx, queues):
    app = ctx.obj['app']
    with Connection(redis_store._redis_client), app.test_request_context():
        qs = map(Queue, queues) or [Queue()]
        worker = Worker(qs)
        g.is_rq_process = True

        sentry = app.extensions.get('sentry')
        if sentry is not None:
            from rq.contrib.sentry import register_sentry
            register_sentry(sentry.client, worker)
        worker.work()


_CLEANUP_HOOKS = {
    'clean_printouts': _clean_printouts
}


@rq.command()
@click.option('--hook', '-k', help='hook after cleaning up jobs')
@click.pass_context
def cleanup(ctx, hook):
    """ delete failed jobs from redis """
    app = ctx.obj['app']
    with Connection(redis_store._redis_client):
        failed = get_failed_queue()
        count = failed.count
        failed.empty()
        click.echo('%s number of failed jobs cleared from redis' % count)

    """ delete jobs that are older than a month """
    now = datetime.now()
    since = now - relativedelta(months=1)
    with app.app_context():
        jobs = Job.query.filter(Job.date <= since)
        count = jobs.count()
        results = [j.result for j in jobs]
        jobs.delete()
        db.session.commit()
        click.echo('%s number of jobs cleared from postgres' % count)

        if hook in _CLEANUP_HOOKS:
            cleanup_count = _CLEANUP_HOOKS[hook](results)
            click.echo('%s number of items cleaned from %s' %
                       (cleanup_count, hook))


@cli.command()
@click.pass_context
def meetings(ctx):
    import pprint
    pprint.pprint(get_meetings())


@cli.command()
@click.pass_context
def migrate_hint(ctx):
    app = ctx.obj['app']
    with app.app_context():
        for custom_field in CustomField.query.all():
            if not custom_field.description:
                continue
            hint = Translation(english=custom_field.description)
            db.session.add(hint)
            db.session.flush()
            custom_field.hint = hint
        db.session.commit()


@cli.command()
@click.pass_context
def update_representing(ctx):
    app = ctx.obj['app']
    with app.test_request_context():
        for participant in Participant.query.all():
            participant.set_representing()
        db.session.commit()
        click.echo('Updated representing for all participants.')


@cli.command()
@click.pass_context
def remove_missing_countries(ctx):
    app = ctx.obj['app']
    with app.test_request_context():
        for participant in Participant.query.all():
            try:
                if participant.country:
                    participant.country.name
            except KeyError:
                click.echo(u'Removed territory with code %s' %
                           participant.country.code)
                participant.country = None
            try:
                if participant.represented_country:
                    participant.represented_country.name
            except KeyError:
                click.echo(u'Removed territory with code %s' %
                           participant.represented_country.code)
                participant.represented_country = None

        db.session.commit()


@cli.command()
@click.pass_context
def add_verified_flag_mp(ctx):
    app = ctx.obj['app']
    with app.test_request_context():
        for meeting in Meeting.query.all():
            if meeting.settings.get('media_participant_enabled', False):
                if meeting.custom_fields.filter_by(
                        custom_field_type=CustomField.MEDIA,
                        slug='verified').count():
                    continue
                cf = CustomField(slug='verified',
                                 meeting_id=meeting.id,
                                 field_type=CustomField.CHECKBOX,
                                 is_primary=True,
                                 custom_field_type=CustomField.MEDIA)
                cf.label = Translation(english='Acknowledged')
                cf.sort = meeting.custom_fields.filter_by(
                    custom_field_type=CustomField.MEDIA).count() + 1
                db.session.add(cf)
        db.session.commit()


@cli.command()
def compile_translations():
    command = ['pybabel', 'compile', '-d', 'mrt/translations']
    FNULL = open(os.devnull, 'w')
    subprocess.check_call(command, stdout=FNULL, stderr=subprocess.STDOUT)


@cli.command()
@click.pass_context
def sync_cites_meetings(ctx):
    logger.info("Start sync_cites_meetings")
    app = ctx.obj['app']
    cites_meetings_urls = {
        'english': 'https://cites.org/ws/meetings-mrt',
        'french': 'https://cites.org/fra/ws/meetings-mrt',
        'spanish': 'https://cites.org/esp/ws/meetings-mrt',
    }

    retrieved_meetings = defaultdict(dict)
    headers = {'Accept': 'application/json'}

    for language in cites_meetings_urls:
        response = requests.get(cites_meetings_urls[language], headers=headers)
        response.raise_for_status()

        for meeting in response.json():
            unique_id = meeting.get('id', '')
            meeting_dict = retrieved_meetings[unique_id]

            meeting_dict['{}_title'.format(language)] = meeting.get('title', '')
            meeting_dict['{}_city'.format(language)] = meeting.get('city', '')
            meeting_dict['description'] = meeting.get('description', '')
            meeting_dict['meeting_type'] = meeting.get('type', '')
            meeting_dict['start'] = meeting.get('start', '')
            meeting_dict['end'] = meeting.get('end', '')
            meeting_dict['location'] = meeting.get('location', '')
            meeting_dict['country'] = meeting.get('country', '')
            meeting_dict['country_code2'] = meeting.get('country_code2', '')
            meeting_dict['country_code3'] = meeting.get('country_code3', '')
            meeting_dict['meeting_number'] = meeting.get('meeting_number', '')
            meeting_dict['link'] = meeting.get('link', '')
            meeting_dict['acronym'] = meeting_dict['meeting_type'] + meeting_dict['meeting_number']


    count = 0
    with app.test_request_context():
        for meeting in retrieved_meetings:
            meeting_dict = retrieved_meetings[meeting]

            if Meeting.query.filter_by(acronym=meeting_dict['acronym']).count():
                # Meeting already exists
                continue
            else:
                logger.info("Adding meeting %s", meeting_dict['acronym'])
                curr_meeting_type = MeetingType.query.filter_by(label=meeting_dict['meeting_type']).first()
                if not curr_meeting_type:
                    curr_meeting_type = MeetingType(label=meeting_dict['meeting_type'],
                                                    slug=slugify(meeting_dict['meeting_type']))
                    db.session.add(curr_meeting_type)

                date_start = datetime.strptime(
                                re.sub(re.compile('<.*?>'), '', meeting_dict['start']),
                                '%d/%m/%Y')
                date_end = datetime.strptime(
                                re.sub(re.compile('<.*?>'), '', meeting_dict['end']),
                                '%d/%m/%Y')

                curr_meeting = Meeting(acronym=meeting_dict['acronym'],
                                      date_start=date_start,
                                      date_end=date_end)
                curr_meeting.meeting_type = curr_meeting_type
                curr_meeting.venue_country = meeting_dict['country_code2']
                curr_meeting.venue_city = Translation(
                                            english = meeting_dict['english_city'],
                                            french = meeting_dict['french_city'],
                                            spanish = meeting_dict['spanish_city'])
                curr_meeting.title = Translation(
                                            english = meeting_dict['english_title'],
                                            french = meeting_dict['french_title'],
                                            spanish = meeting_dict['spanish_title'])
                db.session.add(curr_meeting)
                count += 1
        db.session.commit()

    logger.info("Added %d meetings", count)
    logger.info("Finished sync_cites_meetings")


@cli.command(name='add_custom_field_gender')
@click.option('--meeting', type=int)
@click.pass_context
def add_custom_field_gender(ctx, meeting):
# previously named add_custom_sex_field(ctx):
    app = ctx.obj['app']

    with app.test_request_context():

        meeting_obj = Meeting.query.filter_by(id=meeting).scalar()

        meetings = [meeting_obj] if meeting_obj else Meeting.query.all()

        for meeting in meetings:
            query = (
                CustomField.query
                .filter_by(slug='gender', meeting=meeting)
            )
            if query.scalar():
                continue

            custom_field = CustomField()
            custom_field.meeting = meeting
            custom_field.slug = 'gender'
            custom_field.label = Translation(english=u'Gender')
            custom_field.required = False
            custom_field.field_type = CustomField.SELECT
            custom_field.is_primary = True

            custom_field.visible_on_registration_form = True
            custom_field.is_protected = True

            db.session.add(custom_field)

            _add_choice_values_for_custom_field(
                custom_field, Participant.GENDER_CHOICES)

            click.echo(u'Gender field added for meeting %s \n' % meeting.id)

        db.session.commit()


@cli.command(
    help="""
        Delete custom field values specified by the `--field-names`
        argument or listed in the file provided by `--field-names-file`
        for which: the meeting does not have online registration enabled
        and the date interval is in the past (is a finished meeting).
        If the custom field is of type DOCUMENT or IMAGE, the file will
        also be removed from the disk.
    """
)
@click.pass_context
@click.option("--count-only", is_flag=True, help="Count only without deleting.")
@click.option(
    "--field-names",
    type=str,
    multiple=True,
    help="Comma separated list of field names to delete.",
)
@click.option(
    "--field-names-file",
    type=str,
    help="File with a list of field names to delete.",
)
@click.option(
    "--batch-size",
    type=int,
    default=300,
    help="Batch size for deletion.",
)
def remove_unregistered_users_sensitive_data(ctx, count_only, field_names, field_names_file, batch_size):
    def commit_changes_and_delete_disk_files(filenames_to_delete):
        db.session.commit()
        print("Deleting %s files from disk..." % len(filenames_to_delete))
        for filename in filenames_to_delete:
            unlink_participant_custom_file(filename)

    if not field_names and not field_names_file:
        print(
            "INFO: You must provide at least one of --field-names or "
            "--field-names-file."
        )
        return

    if field_names_file:
        fd = open(field_names_file, "r")
        field_names = json.load(fd)
        fd.close()

    app = ctx.obj["app"]
    with app.app_context():
        cf_values = (
            CustomFieldValue.query.join(CustomField)
            .join(Meeting, CustomField.meeting_id == Meeting.id)
            .filter(~Meeting.online_registration)
            .filter(
                Meeting.date_end < datetime.now(),
                Meeting.date_start < datetime.now(),
            )
            .filter(CustomField.slug.in_(field_names))
        )
        cf_values_count = cf_values.count()
        cf_values_filenames = cf_values.filter(
            or_(
                CustomField.field_type == CustomField.DOCUMENT,
                CustomField.field_type == CustomField.IMAGE,
            )
        ).with_entities(CustomFieldValue.value)

        print(
            "There are %s custom field values and %s files on disk to delete"
            % (cf_values_count, cf_values_filenames.count())
        )
        if count_only or cf_values_count == 0:
            return

        filenames_to_delete = []
        for idx, cf_value in enumerate(cf_values, start=1):
            is_file = (
                cf_value.custom_field.field_type == CustomField.DOCUMENT
                or cf_value.custom_field.field_type == CustomField.IMAGE
            )
            db.session.delete(cf_value)
            if is_file:
                filenames_to_delete.append(cf_value.value)

            if idx % batch_size == 0:
                print(
                    "%s/%s Deleting batch from the database..."
                    % (idx, cf_values_count)
                )
                commit_changes_and_delete_disk_files(filenames_to_delete)
                filenames_to_delete = []

        # Commit the last batch
        print(
            "Deleting last batch from the database..."
        )
        commit_changes_and_delete_disk_files(filenames_to_delete)

        # Count the remaining values
        cf_values_count_after = (
            CustomFieldValue.query
            .join(CustomField)
            .join(Meeting, CustomField.meeting_id == Meeting.id)
            .filter(~Meeting.online_registration)
            .filter(
                Meeting.date_end < datetime.now(),
                Meeting.date_start < datetime.now(),
            )
            .filter(CustomField.slug.in_(field_names))
            .count()
        )

        print("Deleted %s values" % (cf_values_count - cf_values_count_after))


@cli.command(
    help="""
        Delete custom field values that are of type DOCUMENT or IMAGE and
        are not present on the disk.
    """
)
@click.pass_context
@click.option("--count-only", is_flag=True, help="Count only without deleting")
@click.option(
    "--batch-size",
    type=int,
    default=1000,
    help="Batch size for deletion",
)
def delete_ghost_custom_field_value_objs(ctx, count_only, batch_size):
    app = ctx.obj["app"]
    with app.app_context():
        dir_path = app.config['UPLOADED_CUSTOM_DEST']
        cf_values = (
            CustomFieldValue.query
            .join(CustomField)
            .filter(
                or_(
                    CustomField.field_type == CustomField.DOCUMENT,
                    CustomField.field_type == CustomField.IMAGE
                )
            )
            .with_entities(CustomFieldValue.value)
            .all()
        )

        disk_filenames = set(str(file) for file in os.listdir(dir_path))
        db_filenames = set(str(value[0]) for value in cf_values)

        ghost_objs = db_filenames - disk_filenames
        print("There are %s ghost objects to delete" % len(ghost_objs))

        if count_only or len(ghost_objs) == 0:
            return

        # Delete ghost objects
        for idx, cf_value in enumerate(cf_values):
            if cf_value.value in ghost_objs:
                db.session.delete(cf_value)

            if idx % batch_size == 0 and idx != 0:
                print("%s/%s Deleting batch from the database..." % (idx, len(db_filenames)))
                db.session.commit()
            db.session.commit()


@cli.command(
    help="""
        Delete files on disk from /custom_uploads that are not present in the
        database.
    """
)
@click.pass_context
@click.option("--count-only", is_flag=True, help="Count only without deleting")
@click.option(
    "--batch-size",
    type=int,
    default=1000,
    help="Batch size for deletion",
)
def delete_ghost_custom_field_value_files(ctx, count_only, batch_size):
    app = ctx.obj["app"]
    with app.app_context():
        dir_path = app.config['UPLOADED_CUSTOM_DEST']
        cf_values = (
            CustomFieldValue.query
            .join(CustomField)
            .filter(
                or_(
                    CustomField.field_type == CustomField.DOCUMENT,
                    CustomField.field_type == CustomField.IMAGE
                )
            )
            .with_entities(CustomFieldValue.value)
            .all()
        )

        disk_filenames = set(str(file) for file in os.listdir(dir_path))
        db_filenames = set(str(value[0]) for value in cf_values)
        ghost_files = disk_filenames - db_filenames
        print("There are %s ghost files to delete" % len(ghost_files))

        if count_only or len(ghost_files) == 0:
            return

        for filename in ghost_files:
            print("Deleting %s" % filename)
            unlink_participant_custom_file(filename)
