import click
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import mapper, sessionmaker


class Meeting(object):
    pass


def _session(uri):
    engine = create_engine(uri, echo=True)
    meeting = Table('meeting', MetaData(engine), autoload=True)
    mapper(Meeting, meeting)
    return sessionmaker(bind=engine)()


@click.group()
def cli():
    pass


@cli.command(name='import')
@click.argument('database')
@click.pass_context
def import_(ctx, database):
    uri_from_config = ctx.obj['app'].config['SQLALCHEMY_DATABASE_URI']
    uri = '%s/%s' % (uri_from_config.rsplit('/', 1)[0], database)
    ses = _session(uri)
    print ses.query(Meeting).all()
