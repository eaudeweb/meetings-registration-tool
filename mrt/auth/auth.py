from flask import render_template, request, redirect, url_for
from flask.views import MethodView
from flask.ext.login import login_user, logout_user

from mrt.forms.auth import LoginForm


class Login(MethodView):

    def get(self):
        form = LoginForm()
        next = request.values.get('next')

        return render_template('auth/login.html', form=form, next=next)

    def post(self):
        form = LoginForm(request.form)
        next = request.values.get('next')

        if form.validate():
            user = form.get_user()
            login_user(user)
            return redirect(next or url_for('temp'))

        return render_template('auth/login.html', form=form, next=next)


class Logout(MethodView):

    def get(self):
        logout_user()
        return redirect(url_for('temp'))

#@auth.route('/login', methods=['GET', 'POST'])
#def login():
#    form = LoginForm(request.form)
#    next = request.values.get('next')
#    if request.method == 'POST' and form.validate():
#        user = form.get_user()
#        login_user(user)
#        return redirect(next or url_for('temp'))
#    return render_template('auth/login.html', form=form, next=next)
#
#
#@auth.route('/logout')
#@login_required
#def logout():
#    logout_user()
#    return redirect(url_for('temp'))
