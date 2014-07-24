
from pytest import fixture
from mrt.app import create_app
from mrt.models import db


@fixture
def app(request, tmpdir):
    test_config = {
        'SECRET_KEY': 'test',
        'ASSETS_DEBUG': True,
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite://',
        'UPLOADED_BACKGROUNDS_DEST': str(tmpdir.join('backgrounds')),
        'HOSTNAME': 'http://meetings.edw.ro/',
        'DEFAULT_MAIL_SENDER': 'noreply',
    }

    app = create_app(test_config)
    app_context = app.app_context()
    app_context.push()

    db.create_all()

    @request.addfinalizer
    def fin():
        app_context.pop()
        tmpdir.remove(rec=1)

    return app
