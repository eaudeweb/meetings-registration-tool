
import jinja2
import shutil

from pytest import fixture
from path import path

from mrt.app import create_app
from mrt.models import db
from mrt.pdf import PdfRenderer
from .factories import UserFactory, MeetingFactory
from .factories import MeetingTypeFactory, StaffFactory


@fixture
def app(request, tmpdir):
    templates_path = tmpdir.ensure_dir('templates')
    backgrounds_path = path(tmpdir.ensure_dir('backgrounds'))
    custom_uploads_path = path(tmpdir.ensure_dir('custom_uploads'))
    thumb_path = path(tmpdir.ensure_dir('thumbnails'))
    crop_path = path(tmpdir.ensure_dir('crops'))
    printouts_path = path(tmpdir.ensure_dir('printouts'))

    test_config = {
        'SECRET_KEY': 'test',
        'ASSETS_DEBUG': True,
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite://',
        'UPLOADED_BACKGROUNDS_DEST': backgrounds_path,
        'UPLOADED_CUSTOM_DEST': custom_uploads_path,
        'UPLOADED_PRINTOUTS_DEST': printouts_path,
        'UPLOADED_THUMBNAIL_DEST': thumb_path,
        'UPLOADED_CROP_DEST': crop_path,
        'MEDIA_THUMBNAIL_FOLDER': thumb_path,
        'MEDIA_FOLDER': path(tmpdir),
        'HOSTNAME': 'http://meetings.edw.ro/',
        'DEFAULT_MAIL_SENDER': 'noreply',
        'TEMPLATES_PATH': templates_path,
        'MAIL_SUPPRESS_SEND': True,
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
    user = UserFactory(is_superuser=True, email='admin@test.com')
    StaffFactory(user=user)
    return user


@fixture
def default_meeting_type():
    meeting_type = MeetingTypeFactory(slug='def', default=True)
    return meeting_type


@fixture
def default_meeting():
    meeting_type = default_meeting_type()
    default_meeting = MeetingFactory(meeting_type=meeting_type,
                                     title__english='Default')
    return default_meeting


@fixture
def pdf_renderer(app):
    path = app.config['TEMPLATES_PATH'] / 'template.html'
    output = 'Lorem ipsum dolor sit amet'
    with path.open('w+') as f:
        f.write(output)

    # Mock _generate_pdf to not use external commands
    class RendererMock(PdfRenderer):
        content = output

        def _generate_pdf(self):
            shutil.copy2(self.template_path, self.pdf_path)

    return RendererMock
