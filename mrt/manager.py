from datetime import datetime
from dateutil.relativedelta import relativedelta
import click
import code

from flask import g
from alembic.config import CommandLine
from rq import Queue, Connection, Worker
from rq import get_failed_queue

from mrt.models import redis_store
from mrt.models import User, db, Staff, Job
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
def create_superuser(ctx):
    email = click.prompt('Enter email', type=str)
    while not validate_email(email):
        email = click.prompt('Invalid email. Enter another email', type=str)
    password = click.prompt('Enter password', type=str, hide_input=True)
    confirm = click.prompt('Enter password again', type=str, hide_input=True)

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
