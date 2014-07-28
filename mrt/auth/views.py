from flask import render_template, request, redirect, url_for, flash
from flask.views import MethodView
from flask.ext.login import login_user, logout_user, login_required

from mrt.forms import auth
from mrt.models import db, User
from mrt.mail import send_reset_mail


class Login(MethodView):

    def get(self):
        form = auth.LoginForm()
        next = request.values.get('next')
        return render_template('auth/login.html', form=form, next=next)

    def post(self):
        form = auth.LoginForm(request.form)
        next = request.values.get('next')
        if form.validate():
            user = form.get_user()
            login_user(user)
            return redirect(next or url_for('meetings.home'))
        return render_template('auth/login.html', form=form, next=next)


class Logout(MethodView):

    def get(self):
        logout_user()
        return redirect(url_for('auth.login'))


class RecoverPassword(MethodView):

    def get(self):
        form = auth.RecoverForm()
        return render_template('auth/forgot_password.html', form=form)

    def post(self):
        form = auth.RecoverForm(request.form)
        if form.validate():
            user = form.save()
            send_reset_mail(user.email, user.recover_token)
            flash('Please check your email', 'success')
            return redirect(url_for('auth.login'))
        return render_template('auth/forgot_password.html', form=form)


class ChangePassword(MethodView):

    decorators = (login_required, )

    def get(self):
        form = auth.ChangePasswordForm()
        return render_template('auth/change_password.html', form=form)

    def post(self):
        form = auth.ChangePasswordForm(request.form)
        if form.validate():
            form.save()
            flash('Password changed succesfully', 'success')
            return redirect(url_for('meetings.home'))
        return render_template('auth/change_password.html', form=form)


class ResetPassword(MethodView):

    def get(self, token):
        form = auth.ResetPasswordForm()
        user = User.query.filter_by(recover_token=token).first()
        if user is None or not user.token_is_active:
            flash('Invalid token', 'danger')
            return redirect(url_for('auth.login'))

        return render_template('auth/reset_password.html', form=form)

    def post(self, token):
        form = auth.ResetPasswordForm(request.form)
        user = User.query.filter_by(recover_token=token).first()
        if user is None or not user.token_is_active:
            flash('Invalid token', 'danger')
            return redirect(url_for('auth.login'))

        if form.validate():
            user.set_password(form.password.data)
            user.is_active = True
            db.session.commit()
            flash('Password changed succesfully', 'success')
            return redirect(url_for('auth.login'))
        return render_template('auth/reset_password.html', form=form)
