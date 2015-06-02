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
def aewa():
    enviroment('aewa')


@task
def cites():
    enviroment('cites')


@task
def cms():
    enviroment('cms')


@task
def deploy():
    require('deployment_location', used_for=USED_FOR_MSG)
    if hasattr(env, 'brand_path'):
        with cd(env.brand_path), prefix('source %(sandbox_activate)s' % env):
            run('git pull --rebase')

    with cd(env.project_root), prefix('source %(sandbox_activate)s' % env):
        run('git pull --rebase')
        run('pip install -r requirements-dep.txt')
        run('python manage.py alembic upgrade head')
        run('supervisorctl -c %(supervisord_conf)s restart all' % env)
