
import jinja2

from pytest import fixture
from path import path

from mrt.app import create_app
from mrt.models import db, Meeting
from .factories import RoleUserFactory, StaffFactory, MeetingFactory


@fixture
def app(request, tmpdir):
    templates_path = tmpdir.ensure_dir('templates')
    backgrounds_path = path(tmpdir.ensure_dir('backgrounds'))
    custom_uploads_path = path(tmpdir.ensure_dir('custom_uploads'))
    thumb_path = path(tmpdir.ensure_dir('thumbnails'))

    test_config = {
        'SECRET_KEY': 'test',
        'ASSETS_DEBUG': True,
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite://',
        'UPLOADED_BACKGROUNDS_DEST': backgrounds_path,
        'UPLOADED_CUSTOM_DEST': custom_uploads_path,
        'UPLOADED_THUMBNAIL_DEST': thumb_path,
        'MEDIA_THUMBNAIL_FOLDER': thumb_path,
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


@fixture
def default_meeting():
    default_meeting = MeetingFactory(meeting_type=Meeting.DEFAULT_TYPE)
    return default_meeting
