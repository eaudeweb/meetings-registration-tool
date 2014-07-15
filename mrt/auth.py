from flask import render_template, Blueprint, request, redirect, url_for
from flask.ext.login import login_user, logout_user, login_required

from mrt.forms.auth import LoginForm

auth = Blueprint("auth", __name__)


def initialize_app(app):
    app.register_blueprint(auth)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    next = request.values.get('next')
    if request.method == 'POST' and form.validate():
        user = form.get_user()
        login_user(user)
        return redirect(next or url_for('temp'))
    return render_template('auth/login.html', form=form, next=next)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('temp'))
