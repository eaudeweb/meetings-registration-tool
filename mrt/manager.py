from datetime import datetime
from dateutil.relativedelta import relativedelta
import click
import code

from flask import g
from alembic.config import CommandLine
from rq import Queue, Connection, Worker
from rq import get_failed_queue

from mrt.models import get_or_create_role, redis_store
from mrt.models import User, db, Staff, RoleUser, Job


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
    password = click.prompt('Enter password', type=str, hide_input=True)
    confirm = click.prompt('Enter password again', type=str, hide_input=True)

    if password == confirm:
        app = ctx.obj['app']
        with app.app_context():
            user = User(email=email)
            user.set_password(password)
            db.session.add(user)
            role = get_or_create_role('Admin')
            role_user = RoleUser(role=role, user=user)
            db.session.add(role_user)
            staff = Staff(user=user, full_name='')
            db.session.add(staff)
            db.session.commit()
            click.echo('User has been created')
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
    with Connection(redis_store.connection), app.test_request_context():
        qs = map(Queue, queues) or [Queue()]
        worker = Worker(qs)
        g.is_rq_process = True
        worker.work()


@rq.command()
@click.pass_context
def cleanup(ctx):
    """ delete failed jobs from redis """
    app = ctx.obj['app']
    with Connection(redis_store.connection):
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
        jobs.delete()
        db.session.commit()
        click.echo('%s number of jobs cleared from postgres' % count)
