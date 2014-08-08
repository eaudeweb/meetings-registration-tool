from werkzeug import SharedDataMiddleware

from flask import Flask, redirect, url_for
from flask.ext.babel import Babel
from flask.ext.login import LoginManager
from flask.ext.thumbnails import Thumbnail
from flask.ext.uploads import configure_uploads, patch_request_class

from raven.contrib.flask import Sentry
from path import path

from mrt.models import db, User
from mrt.assets import assets_env

from mrt.meetings.urls import meetings
from mrt.admin.urls import admin
from mrt.auth.urls import auth
from mrt.mail import mail

from mrt.template import nl2br, active, date_processor
from mrt.forms.admin import backgrounds
from mrt.forms.meetings import custom_upload


def create_app(config={}):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_pyfile('settings.py')
    app.config.update(config)
    app.debug = True

    Babel(app)
    assets_env.init_app(app)
    db.init_app(app)

    app.register_blueprint(meetings)
    app.register_blueprint(auth)
    app.register_blueprint(admin)

    app.add_template_filter(nl2br)
    app.add_template_global(active)
    app.add_template_global(date_processor)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    mail.init_app(app)

    Sentry(app)

    _configure_uploads(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)

    @app.route('/')
    def index():
        return redirect(url_for('meetings.home'))

    return app


def _configure_uploads(app):
    files_path = path(app.instance_path) / 'files'

    if 'UPLOADED_BACKGROUNDS_DEST' not in app.config:
        app.config['UPLOADED_BACKGROUNDS_DEST'] = files_path / 'backgrounds'
    if 'UPLOADED_CUSTOM_DEST' not in app.config:
        app.config['UPLOADED_CUSTOM_DEST'] = files_path / 'custom_uploads'

    if 'MEDIA_FOLDER' not in app.config:
        app.config['MEDIA_FOLDER'] = files_path / 'custom_uploads'
    if 'MEDIA_THUMBNAIL_FOLDER' not in app.config:
        app.config['MEDIA_THUMBNAIL_FOLDER'] = files_path / 'thumbnails'
    if 'MEDIA_THUMBNAIL_URL' not in app.config:
        app.config['MEDIA_THUMBNAIL_URL'] = '/static/files/thumbnails/'

    app.add_url_rule('/static/files/<filename>', 'files', build_only=True)
    app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
        '/static/files': files_path
    })

    patch_request_class(app, 1 * 1024 * 1024)  # limit upload size to 1MB
    configure_uploads(app, (backgrounds, custom_upload))
    Thumbnail(app)
