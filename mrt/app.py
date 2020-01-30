import logging
import logging.config
import importlib
import traceback

import sentry_sdk
from flask import request
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.rq import RqIntegration
from werkzeug import SharedDataMiddleware
from werkzeug.contrib.fixers import ProxyFix
from flask import Flask, redirect, render_template, url_for, g
from flask_babel import Babel
from flask_login import LoginManager, current_user as user
from flask_thumbnails import Thumbnail
from flask_uploads import configure_uploads, patch_request_class

from path import Path
from werkzeug.urls import url_encode

from mrt.common import ProtectedStaticFiles
from mrt.definitions import LANGUAGES_MAP
from mrt.admin.urls import admin
from mrt.assets import assets_env
from mrt.auth.urls import auth

from mrt.forms.admin import backgrounds
from mrt.forms.meetings import logos_upload
from mrt.forms.fields import custom_upload

from mrt.mail import mail
from mrt.meetings.urls import meetings
from mrt.models import db, redis_store, User, CustomField, Participant


from mrt.template import convert_to_dict, has_perm, url_external
from mrt.template import region_in
from mrt.custom_country import country_in
from mrt.template import inject_badge_context
from mrt.template import nl2br, active, date_processor, countries, crop
from mrt.template import no_image_cache, activity_map, inject_static_file
from mrt.template import pluralize, clean_html, year_processor
from mrt.template import sort_by_tuple_element
from mrt.utils import slugify, Logo


_DEFAULT_LANG = 'english'
_TRANSLATIONS = [_DEFAULT_LANG, 'french', 'spanish']
_TITLE_CHOICES = ['Ms', 'Mr', 'Dr', 'Prof']


DEFAULT_CONFIG = {
    'REDIS_URL': 'redis://localhost:6379/0',
    'DEBUG': True,
    'ASSETS_DEBUG': True,
    'MAIL_SUPPRESS_SEND': True,
    # Branding defaults
    'PRODUCT_LOGO': '',
    'PRODUCT_SIDE_LOGO': '',
    'DEFAULT_PHRASES_PATH': (
        Path(__file__).abspath().parent / 'fixtures' / 'default_phrases.json'),
    'MAIL_DEFAULT_SENDER': '',
    'DEFAULT_LANG': _DEFAULT_LANG,
    'TRANSLATIONS': _TRANSLATIONS,
    'TITLE_CHOICES': _TITLE_CHOICES,
}


def register_monitoring_views(app):

    @app.route('/crash')
    def crash():
        raise ValueError("Crashing as requested")


# skip logging for tests
def create_app(config={}, skip_logging=False):
    app = Flask(__name__, instance_relative_config=True)
    app.config.update(DEFAULT_CONFIG)
    app.config.from_pyfile('settings.py', silent=True)
    app.config.update(config)

    babel = Babel(app)

    @babel.localeselector
    def get_locale():
        return getattr(g, 'language', 'en')

    assets_env.init_app(app)
    db.init_app(app)

    blueprints = app.config.get('BLUEPRINTS', [])
    for blueprint in blueprints:
        module = importlib.import_module('contrib.{}.urls'.format(blueprint))
        app.register_blueprint(module.blueprint)

    app.register_blueprint(admin)
    app.register_blueprint(auth)
    app.register_blueprint(meetings)
    register_monitoring_views(app)

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
    app.add_template_filter(clean_html)
    app.add_template_global(active)
    app.add_template_global(date_processor)
    app.add_template_global(year_processor)
    app.add_template_global(inject_static_file)
    app.add_template_global(inject_badge_context)
    app.add_template_global(has_perm)
    app.add_template_global(url_external)
    app.add_template_global(Logo, name='get_logo')

    @app.template_global()
    def modify_query(**new_values):
        args = request.args.copy()

        for key, value in new_values.items():
            args[key] = value

        return '{}?{}'.format(request.path, url_encode(args))

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
                'LANGUAGE': CustomField.LANGUAGE,
                'CATEGORY': CustomField.CATEGORY,
                'EVENT': CustomField.EVENT,
            },
            'Participant': {
                'PARTICIPANT': Participant.PARTICIPANT,
                'MEDIA': Participant.MEDIA,
                'DEFAULT': Participant.DEFAULT,
                'DEFAULT_MEDIA': Participant.DEFAULT_MEDIA,
            },
            'LANGUAGES_MAP': LANGUAGES_MAP,
        }

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'

    mail.init_app(app)
    redis_store.init_app(app)

    _configure_uploads(app)
    if not skip_logging:
        _configure_logging(app)
    _configure_healthcheck(app)

    app.wsgi_app = ProxyFix(app.wsgi_app)
    if not app.config.get('DEBUG') and app.config.get('SENTRY_DSN'):
        sentry_sdk.init(
            app.config.get('SENTRY_DSN'),
            integrations=[RqIntegration(), FlaskIntegration(), LoggingIntegration()]
        )

    app.config['REPRESENTING_TEMPLATES'] = (
        Path('meetings/participant/representing'))

    _translations = app.config['TRANSLATIONS']
    if _DEFAULT_LANG not in _translations:
        _translations = [_DEFAULT_LANG] + _translations
    app.config['TRANSLATIONS'] = _translations

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)

    @app.route('/')
    def index():
        return redirect(url_for('meetings.home'))

    @app.errorhandler(413)
    def file_too_large(error):
        mb = 1024 * 1024
        max_size = app.config.get('MAX_UPLOAD_SIZE', mb) / mb
        return render_template('_file_too_large.html', max_size=max_size), 413

    return app


def _configure_uploads(app):
    app.config['FILES_PATH'] = files_path = Path(app.instance_path) / 'files'
    app.config['PATH_BACKGROUNDS_KEY'] = path_backgrounds_key = 'backgrounds'
    app.config['PATH_CROP_KEY'] = path_crop_key = 'crops'
    app.config['PATH_CUSTOM_KEY'] = path_custom_key = 'custom_uploads'
    app.config['PATH_LOGOS_KEY'] = path_logos_key = 'logos'
    app.config['PATH_THUMB_KEY'] = path_thumb_key = 'thumbnails'
    app.config['PATH_PRINTOUTS_KEY'] = path_printouts_key = 'printouts'

    if 'UPLOADED_BACKGROUNDS_DEST' not in app.config:
        app.config['UPLOADED_BACKGROUNDS_DEST'] = (files_path /
                                                   path_backgrounds_key)
    if 'UPLOADED_CROP_DEST' not in app.config:
        app.config['UPLOADED_CROP_DEST'] = files_path / path_crop_key
    if 'UPLOADED_CUSTOM_DEST' not in app.config:
        app.config['UPLOADED_CUSTOM_DEST'] = files_path / path_custom_key
    if 'UPLOADED_LOGOS_DEST' not in app.config:
        app.config['UPLOADED_LOGOS_DEST'] = files_path / path_logos_key
    if 'UPLOADED_PRINTOUTS_DEST' not in app.config:
        app.config['UPLOADED_PRINTOUTS_DEST'] = files_path / path_printouts_key

    # ensure logos and printouts folders exist
    app.config['UPLOADED_LOGOS_DEST'].makedirs_p()
    app.config['UPLOADED_PRINTOUTS_DEST'].makedirs_p()

    if 'MEDIA_FOLDER' not in app.config:
        app.config['MEDIA_FOLDER'] = files_path
    if 'MEDIA_THUMBNAIL_FOLDER' not in app.config:
        app.config['MEDIA_THUMBNAIL_FOLDER'] = \
            app.config['UPLOADED_THUMBNAIL_DEST'] = files_path / path_thumb_key
    app.config['MEDIA_THUMBNAIL_URL'] = '/static/files/thumbnails/'

    app.add_url_rule("/static/files/<path:filename>", view_func=ProtectedStaticFiles.as_view("files"))

    # limit upload size to 1MB
    patch_request_class(app, app.config.get(
        'MAX_UPLOAD_SIZE', 1 * 1024 * 1024))
    configure_uploads(app, (backgrounds, custom_upload, logos_upload))
    Thumbnail(app)


def _configure_logging(app):
    if app.config.has_key('LOGGING'):
        try:
            # XXX Temporary code to prevent production deployments
            #  that have old settings files with raven from crashing.
            del app.config["LOGGING"]["handlers"]["sentry"]
        except KeyError:
            pass
        logging.config.dictConfig(app.config['LOGGING'])
    else:
        logging.basicConfig()
    logger = logging.getLogger("mrt")

    @app.errorhandler(Exception)
    def exceptions(e):
        tb = traceback.format_exc()
        logger.error('%s\n %s %s %s %s %s %s',
                     e,
                     request.referrer,
                     request.remote_addr,
                     request.method,
                     request.scheme,
                     request.path,
                     tb, extra={'request': request, 'user': user, 'stack': True})
        return "Something went wrong. The webmaster has been notified about \
            this error and our team will fix it asap.", 500


def _configure_healthcheck(app):

    @app.route('/healthcheck')
    def healthcheck():
        return ('', 204)
