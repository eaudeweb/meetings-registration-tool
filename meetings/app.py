from flask import Flask


def create_app(config={}):
    app = Flask(__name__, instance_relative_config=True)
    app.config.update(config)
    return app
