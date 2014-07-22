from flask import render_template, request, redirect, url_for, flash
from flask.views import MethodView
from flask.ext.login import login_user, logout_user

from mrt.forms.auth import LoginForm, RecoverForm, ResetPasswordForm
from mrt.models import db, User
from mrt.mail import send_reset_mail


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
            return redirect(next or url_for('meetings.home'))
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
            user = form.save()
            send_reset_mail(user.email, user.recover_token)
            return redirect(url_for('meetings.home'))
        return render_template('auth/recover.html', form=form)


class ResetPassword(MethodView):

    def get(self, token):
        form = ResetPasswordForm()
        user = User.query.filter_by(recover_token=token).first()
        if user is None or not user.token_is_active:
            flash('Invalid token')
            return redirect(url_for('meetings.home'))

        return render_template('auth/reset_password.html', form=form)

    def post(self, token):
        form = ResetPasswordForm(request.form)
        user = User.query.filter_by(recover_token=token).first()
        if user is None or not user.token_is_active:
            flash('Invalid token')
            return redirect(url_for('meetings.home'))

        if form.validate():
            user.set_password(form.password.data)
            user.is_active = True
            db.session.commit()
            flash('Password changed succesfully')
            return redirect(url_for('auth.login'))
        return render_template('auth/reset_password.html', form=form)
