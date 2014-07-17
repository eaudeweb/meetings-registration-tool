from flask import Flask
from flask.ext.login import LoginManager
from flask.ext.babel import Babel

from mrt import auth
from mrt.models import db, User
from mrt.assets import assets_env

from mrt.meetings.urls import meetings
from mrt.admin.urls import admin


def create_app(config={}):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_pyfile('settings.py')
    app.config.update(config)
    app.debug = True

    Babel(app)
    assets_env.init_app(app)
    db.init_app(app)

    app.register_blueprint(meetings)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    auth.initialize_app(app)
    app.register_blueprint(admin)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)

    @app.route('/')
    def temp():
        from flask import render_template
        return render_template('_layout.html')
    return app
