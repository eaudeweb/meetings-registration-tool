from flask import Flask
from meetings.models import db
from meetings.assets import assets_env


def create_app(config={}):
    app = Flask(__name__, instance_relative_config=True)
    app.config.update(config)
    app.config.from_pyfile('settings.py')

    assets_env.init_app(app)
    db.init_app(app)

    @app.route('/')
    def temp():
        from flask import render_template
        return render_template('_layout.html')
    return app
