from collections import OrderedDict

from flask import render_template, jsonify, flash, abort, url_for
from flask.ext.login import login_required, current_user
from flask.views import MethodView

from mrt.forms.auth import RecoverForm
from mrt.mail import send_reset_mail
from mrt.meetings import PermissionRequiredMixin
from mrt.models import User, db, Participant


def _get_users_with_participants(limit=10, offset=0):
    qs = (User.query.outerjoin(Participant).with_entities(User, Participant)
          .order_by(User.id.asc())
          .limit(limit).offset(offset))
    groups = OrderedDict()
    for user, participant in qs:
        groups.setdefault(user, [])
        if participant:
            groups[user].append(participant)
    return groups


class Users(PermissionRequiredMixin, MethodView):

    decorators = (login_required,)
    permission_required = ('manage_default',)

    def get(self):
        users = _get_users_with_participants()
        return render_template('admin/user/list.html', users=users)


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
