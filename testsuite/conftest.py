
import jinja2

from pytest import fixture
from mrt.app import create_app
from mrt.models import db

from .factories import RoleUserFactory, StaffFactory


@fixture
def app(request, tmpdir):
    templates_path = tmpdir.ensure_dir('templates')
    test_config = {
        'SECRET_KEY': 'test',
        'ASSETS_DEBUG': True,
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite://',
        'UPLOADED_BACKGROUNDS_DEST': str(tmpdir.join('backgrounds')),
        'HOSTNAME': 'http://meetings.edw.ro/',
        'DEFAULT_MAIL_SENDER': 'noreply',
        'TEMPLATES_PATH': templates_path,
    }

    app = create_app(test_config)
    app_context = app.app_context()
    app_context.push()
    app.jinja_loader = jinja2.ChoiceLoader([
        app.jinja_loader,
        jinja2.FileSystemLoader([str(templates_path)])
    ])

    db.create_all()

    app.client = app.test_client()

    @request.addfinalizer
    def fin():
        app_context.pop()
        tmpdir.remove(rec=1)

    return app


@fixture
def user():
    role_user = RoleUserFactory()
    StaffFactory(user=role_user.user)

    return role_user.user
