from flask import Flask
from meetings.models import db


def create_app(config={}):
    app = Flask(__name__, instance_relative_config=True)
    app.config.update(config)
    app.config.from_pyfile('settings.py')
    db.init_app(app)

    @app.route('/')
    def temp():
        pass

    return app
