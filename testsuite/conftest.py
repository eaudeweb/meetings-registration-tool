import os

from pytest import fixture
from mrt.app import create_app
from mrt.models import db
from tempfile import mkdtemp

TEST_DIR = mkdtemp()
TEST_CONFIG = {
    'SECRET_KEY': 'test',
    'ASSETS_DEBUG': True,
    'TESTING': True,
    'SQLALCHEMY_DATABASE_URI': 'sqlite://',
    'UPLOADED_BACKGROUNDS_DEST': os.path.join(TEST_DIR, 'files', 'backgrounds')
}


@fixture
def app(request):
    app = create_app(TEST_CONFIG)
    app_context = app.app_context()
    app_context.push()

    db.create_all()

    @request.addfinalizer
    def fin():
        app_context.pop()

    return app
