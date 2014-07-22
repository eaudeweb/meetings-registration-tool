import os

from flask import Flask
from flask.ext.login import LoginManager
from flask.ext.babel import Babel
from flask.ext.uploads import configure_uploads

from mrt.models import db, User
from mrt.assets import assets_env

from mrt.meetings.urls import meetings
from mrt.admin.urls import admin
from mrt.auth.urls import auth
from mrt.mail import mail

from mrt.template import nl2br, active
from mrt.forms.admin import backgrounds


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
DEFAULT_CONFIG = {
    'UPLOADED_BACKGROUNDS_DEST': os.path.join(
        INSTANCE_DIR, 'files', 'backgrounds'),
}


def create_app(config={}):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_pyfile('settings.py')
    app.config.update(DEFAULT_CONFIG)
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

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    mail.init_app(app)

    configure_uploads(app, (backgrounds,))

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)

    @app.route('/')
    def temp():
        from flask import render_template
        return render_template('_layout.html')
    return app
