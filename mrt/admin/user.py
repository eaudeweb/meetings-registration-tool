from flask import render_template, jsonify, request
from flask import flash
from flask import g, abort
from flask.ext.login import login_required, current_user
from flask.views import MethodView

from mrt.mail import send_reset_mail
from mrt.meetings import PermissionRequiredMixin
from mrt.models import User, db
from mrt.forms.auth import RecoverForm


class Users(PermissionRequiredMixin, MethodView):

    decorators = (login_required,)
    permission_required = ('manage_default',)

    def get(self):
        users = User.query.all()
        return render_template('admin/user/list.html',
                               users=users)


class UserToggle(PermissionRequiredMixin, MethodView):

    decorators = (login_required,)
    permission_required = ('manage_default',)

    def post(self, user_id):
        user = User.query.get_or_404(user_id)
        if user == current_user:
            abort(400)
        user.active = not user.active
        db.session.commit()
        return jsonify(status="success")


class UserPasswordChange(PermissionRequiredMixin, MethodView):

    decorators = (login_required,)
    permission_required = ('manage_default',)

    def get(self, user_id):
        user = User.query.get_or_404(user_id)
        form = RecoverForm(email=user.email)
        return render_template('admin/user/password_form.html', form=form,
                               user=user)

    def post(self, user_id):
        user = User.query.get_or_404(user_id)
        form = RecoverForm(email=user.email)
        if form.validate():
            user = form.save()
            send_reset_mail(user.email, user.recover_token)
            flash('The reset email has been sent successfully', 'success')
            return jsonify(status="success")
        data = render_template('admin/user/password_form.html', form=form,
                               user=user)
        return jsonify(status="error", data=data)
