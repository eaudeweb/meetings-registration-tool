from .models import User, db, Staff, RoleUser

import click
import code
from alembic.config import CommandLine

from mrt.models import get_or_create_role


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
