from flask import Flask
from flask.ext.login import LoginManager

from mrt import auth
from mrt.models import db, User
from mrt.assets import assets_env


def create_app(config={}):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_pyfile('settings.py')
    app.config.update(config)
    app.debug = True

    assets_env.init_app(app)
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)

    auth.initialize_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)

    @app.route('/')
    def temp():
        from flask import render_template
        return render_template('_layout.html')
    return app
