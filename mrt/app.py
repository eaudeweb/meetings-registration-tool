import logging
import sys

from werkzeug import SharedDataMiddleware
from flask import Flask, redirect, request, render_template, url_for, g
from flask.ext.babel import Babel
from flask.ext.login import LoginManager
from flask.ext.thumbnails import Thumbnail
from flask.ext.uploads import configure_uploads, patch_request_class

from path import path

from mrt.admin.urls import admin
from mrt.assets import assets_env
from mrt.auth.urls import auth
from mrt.forms.admin import backgrounds
from mrt.forms.meetings import custom_upload
from mrt.mail import mail
from mrt.meetings.urls import meetings
from mrt.models import db, redis_store, User, CustomField, Participant

from mrt.template import country_in, region_in
from mrt.template import nl2br, active, date_processor, countries, crop
from mrt.template import no_image_cache, activity_map, inject_static_file
from mrt.template import pluralize, url_for_brand_static_path
from mrt.template import sort_by_tuple_element
from mrt.template import convert_to_dict
from mrt.utils import slugify


DEFAULT_CONFIG = {
    'REDIS_URL': 'redis://localhost:6379/0',
    'DEBUG': True,
    'ASSETS_DEBUG': True,
    'MAIL_SUPPRESS_SEND': True,
    # Branding defaults
    'PRODUCT_LOGO': '',
    'PRODUCT_SIDE_LOGO': '',
}


def create_app(config={}):
    app = Flask(__name__, instance_relative_config=True)
    app.config.update(DEFAULT_CONFIG)
    app.config.from_pyfile('settings.py')
    app.config.update(config)

    babel = Babel(app)

    @babel.localeselector
    def get_locale():
        return getattr(g, 'language', 'en')

    assets_env.init_app(app)
    db.init_app(app)

    app.register_blueprint(admin)
    app.register_blueprint(auth)
    app.register_blueprint(meetings)

    app.add_template_filter(activity_map)
    app.add_template_filter(countries)
    app.add_template_filter(country_in)
    app.add_template_filter(region_in)
    app.add_template_filter(crop)
    app.add_template_filter(nl2br)
    app.add_template_filter(convert_to_dict, name='dict')
    app.add_template_filter(no_image_cache)
    app.add_template_filter(pluralize)
    app.add_template_filter(slugify)
    app.add_template_filter(sort_by_tuple_element)
    app.add_template_global(active)
    app.add_template_global(active)
    app.add_template_global(url_for_brand_static_path)
    app.add_template_global(date_processor)
    app.add_template_global(inject_static_file)

    @app.context_processor
    def inject_context():
        return {
            'CustomField': {
                'TEXT': CustomField.TEXT,
                'IMAGE': CustomField.IMAGE,
                'EMAIL': CustomField.EMAIL,
                'CHECKBOX': CustomField.CHECKBOX,
                'SELECT': CustomField.SELECT,
                'COUNTRY': CustomField.COUNTRY,
                'CATEGORY': CustomField.CATEGORY,
            },
            'Participant': {
                'PARTICIPANT': Participant.PARTICIPANT,
                'MEDIA': Participant.MEDIA,
            }
        }

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'

    mail.init_app(app)
    redis_store.init_app(app)

    if app.config.get('SENTRY_DSN'):
        from raven.contrib.flask import Sentry
        Sentry(app)

    _configure_uploads(app)
    _configure_brand(app)
    _configure_logging(app)

    app.config['REPRESENTING_TEMPLATES'] = (
        path('meetings/participant/representing'))

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)

    @app.route('/')
    def index():
        return redirect(url_for('meetings.home'))

    @app.errorhandler(413)
    def file_too_large(error):
        mb = 1024 * 1024
        max_size = app.config.get('UPLOAD_SIZE', mb) / mb
        return render_template('_file_too_large.html',
                               max_size=max_size,
                               url=request.url), 413

    return app


def _configure_uploads(app):
    app.config['FILES_PATH'] = files_path = path(app.instance_path) / 'files'
    app.config['PATH_BACKGROUNDS_KEY'] = path_backgrounds_key = 'backgrounds'
    app.config['PATH_CROP_KEY'] = path_crop_key = 'crops'
    app.config['PATH_CUSTOM_KEY'] = path_custom_key = 'custom_uploads'
    app.config['PATH_LOGOS_KEY'] = path_logos_key = 'logos'
    app.config['PATH_THUMB_KEY'] = path_thumb_key = 'thumbnails'
    app.config['PATH_PRINTOUTS_KEY'] = path_printouts_key = 'printouts'

    if not 'UPLOADED_BACKGROUNDS_DEST' in app.config:
        app.config['UPLOADED_BACKGROUNDS_DEST'] = (files_path /
                                                   path_backgrounds_key)
    if not 'UPLOADED_CROP_DEST' in app.config:
        app.config['UPLOADED_CROP_DEST'] = files_path / path_crop_key
    if not 'UPLOADED_CUSTOM_DEST' in app.config:
        app.config['UPLOADED_CUSTOM_DEST'] = files_path / path_custom_key
    if not 'UPLOADED_LOGOS_DEST' in app.config:
        app.config['UPLOADED_LOGOS_DEST'] = files_path / path_logos_key
    if not 'UPLOADED_PRINTOUTS_DEST' in app.config:
        app.config['UPLOADED_PRINTOUTS_DEST'] = files_path / path_printouts_key

    # ensure logos and printouts folders exist
    app.config['UPLOADED_LOGOS_DEST'].makedirs_p()
    app.config['UPLOADED_PRINTOUTS_DEST'].makedirs_p()

    if not 'MEDIA_FOLDER' in app.config:
        app.config['MEDIA_FOLDER'] = files_path
    if not 'MEDIA_THUMBNAIL_FOLDER' in app.config:
        app.config['MEDIA_THUMBNAIL_FOLDER'] = \
            app.config['UPLOADED_THUMBNAIL_DEST'] = files_path / path_thumb_key
    app.config['MEDIA_THUMBNAIL_URL'] = '/static/files/thumbnails/'

    app.add_url_rule('/static/files/<filename>', 'files', build_only=True)
    app.add_url_rule('/static/brand/<filename>', 'brand', build_only=True)
    app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
        '/static/files': files_path,
        '/static/brand': path(app.instance_path) / 'brand' / 'static'
    })

    # limit upload size to 1MB
    patch_request_class(app, app.config.get('UPLOAD_SIZE', 1 * 1024 * 1024))
    configure_uploads(app, (backgrounds, custom_upload))
    Thumbnail(app)


def _configure_brand(app):
    app.config['BRAND_PATH'] = brand_path = path(app.instance_path) / 'brand'

    if brand_path.exists() and brand_path.isdir():
        app.config.from_pyfile(brand_path / 'settings.py')


def _configure_logging(app):
    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setLevel(logging.INFO)
    app.logger.addHandler(stream_handler)
