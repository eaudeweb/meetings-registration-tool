from flask import render_template, request, redirect, url_for
from flask.views import MethodView
from flask.ext.login import login_user, logout_user

from uuid import uuid4
from datetime import datetime

from mrt.forms.auth import LoginForm, RecoverForm


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


class RecoverPassword(MethodView):

    def get(self):
        form = RecoverForm()
        return render_template('auth/recover.html', form=form)

    def post(self):
        form = RecoverForm(request.form)
        if form.validate():
            form.save()
            #TODO create token and timpstamp on user, send email with url+token
        return render_template('auth/recover.html', form=form)
