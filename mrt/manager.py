from datetime import datetime
from dateutil.relativedelta import relativedelta
import click
import code
import re
import os
import subprocess
import requests
import logging

from flask import g
from alembic.config import CommandLine
from rq import Queue, Connection, Worker
from rq import get_failed_queue

from mrt.models import redis_store, db
from mrt.models import User, Staff, Job
from mrt.models import CustomField, Translation, Participant, Meeting, MeetingType
from mrt.pdf import _clean_printouts
from mrt.scripts.informea import get_meetings
from mrt.utils import validate_email

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
@click.option('--language',
              type=click.Choice(['english', 'french', 'spanish']),
              default='english')
def sync_cites_meetings(ctx, language):
    app = ctx.obj['app']
    cites_meetings_urls = {
        'english': 'https://cites.org/ws/meetings-mrt',
        'french': 'https://cites.org/fra/ws/meetings-mrt',
        'spanish': 'https://cites.org/esp/ws/meetings-mrt',
    }

    headers = {'Accept': 'application/json'}
    response = requests.get(cites_meetings_urls[language], headers=headers)
    response.raise_for_status()

    with app.test_request_context():
        for meeting in Meeting.query.all():
            logging.error(meeting.acronym)

        for meeting in response.json():
            title = meeting.get('title', '')
            description = meeting.get('description', '')
            meeting_type = meeting.get('type', '')
            start = meeting.get('start', '')
            end = meeting.get('end', '')
            location = meeting.get('location', '')
            city = meeting.get('city', '')
            country = meeting.get('country', '')
            country_code2 = meeting.get('country_code2', '')
            country_code3 = meeting.get('country_code3', '')
            meeting_number = meeting.get('meeting_number', '')
            link = meeting.get('link', '')
            acronym = meeting_type + meeting_number

            if Meeting.query.filter_by(acronym=acronym).count():
                # Meeting already exists
                curr_meeting = Meeting.query.filter_by(acronym=acronym).first()

                if language == 'french':
                    curr_meeting.title.french = title
                    curr_meeting.venue_city.french = city
                elif language == 'spanish':
                    curr_meeting.title.spanish = title
                    curr_meeting.venue_city.spanish = city
            else:
                curr_meeting_type = MeetingType.query.filter_by(label=meeting_type).first()
                date_start = datetime.strptime(
                                re.sub(re.compile('<.*?>'), '', start),
                                '%d/%m/%Y')
                date_end = datetime.strptime(
                                re.sub(re.compile('<.*?>'), '', end),
                                '%d/%m/%Y')

                curr_meeting = Meeting(acronym=acronym,
                                      date_start=date_start,
                                      date_end=date_end)
                curr_meeting.meeting_type = curr_meeting_type
                curr_meeting.venue_country = country_code2

                if language == 'english':
                    curr_meeting.title = Translation(english=title)
                    curr_meeting.venue_city = Translation(english=city)

            db.session.add(curr_meeting)
        db.session.commit()

