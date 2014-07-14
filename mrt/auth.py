from flask import render_template, Blueprint, request


auth = Blueprint("auth", __name__)


def initialize_app(app):
    app.register_blueprint(auth)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('auth/login.html')

    return render_template('_layout.html')
