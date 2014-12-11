from itertools import groupby

from flask import render_template, jsonify, flash, abort, url_for
from flask.ext.login import login_required, current_user
from flask.views import MethodView

from mrt.forms.auth import RecoverForm
from mrt.mail import send_reset_mail
from mrt.meetings import PermissionRequiredMixin
from mrt.models import User, db, Participant


class Users(PermissionRequiredMixin, MethodView):

    decorators = (login_required,)
    permission_required = ('manage_default',)

    def get(self):
        participants = (Participant.query.active()
                        .filter(Participant.category != None)
                        .join(Participant.user))
        grouped_participants = groupby(participants, lambda x: x.user)
        return render_template('admin/user/list.html',
                               grouped_participants=grouped_participants)


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

    def post(self, user_id):
        user = User.query.get_or_404(user_id)
        form = RecoverForm(email=user.email)
        if form.validate():
            form.save()
            send_reset_mail(user.email, user.recover_token)
            flash('The reset email has been sent successfully', 'success')
        return jsonify(status="success", url=url_for('.users'))
