import ConfigParser

from fabric.decorators import task
from fabric.operations import require, run
from fabric.context_managers import cd, prefix
from fabric.api import env

from path import path


LOCAL_PATH = path(__file__).abspath().parent
USED_FOR_MSG = """deployment. You need to prefix the task with the location,
    i.e: fab staging deploy."""


def enviroment(location='staging'):
    config = ConfigParser.RawConfigParser()
    config.read(LOCAL_PATH / 'env.ini')
    env.update(config.items(section=location))
    env.sandbox_activate = path(env.sandbox) / 'bin' / 'activate'
    env.deployment_location = location


@task
def staging():
    enviroment('staging')


@task
def deploy():
    require('deployment_location', used_for=USED_FOR_MSG)
    require('project_root', provided_by=[enviroment])

    with cd(env.project_root), prefix('source %(sandbox_activate)s' % env):
        run('git pull --rebase')
        run('pip install -r requirements.txt')
        run('python manage.py alembic upgrade head')
        run('supervisorctl -c %(supervisord_conf)s restart meetings-staging'
            % env)
