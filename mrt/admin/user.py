from flask import render_template, jsonify, flash, abort, url_for
from flask import request
from flask.ext.login import current_user
from flask.views import MethodView

from mrt.admin.mixins import PermissionRequiredMixin
from mrt.forms.auth import RecoverForm
from mrt.mail import send_reset_mail
from mrt.models import User, Meeting, Participant, db


class Users(PermissionRequiredMixin, MethodView):

    def get(self):
        search = request.args.get('search')
        users = User.query.order_by(User.email.asc())
        if search:
            users = users.filter(User.email.contains(search))
        return render_template('admin/user/list.html', users=users)


class UserDetail(PermissionRequiredMixin, MethodView):

    def get(self, user_id):
        user = User.query.filter_by(id=user_id).first_or_404()
        participants = (
            user.participants
            .order_by(Participant.deleted.asc())
            .order_by(Participant.id.asc())
            .filter(Participant.meeting != Meeting.get_default())
        )
        return render_template('admin/user/detail.html',
                               user=user, participants=participants)


class UserToggle(PermissionRequiredMixin, MethodView):

    def post(self, user_id):
        user = User.query.get_or_404(user_id)
        if user == current_user:
            abort(400)
        user.active = not user.active
        db.session.commit()
        return jsonify(status="success")


class UserPasswordChange(PermissionRequiredMixin, MethodView):

    def post(self, user_id):
        user = User.query.get_or_404(user_id)
        form = RecoverForm(email=user.email)
        if form.validate():
            form.save()
            send_reset_mail(user.email, user.recover_token)
            flash('The reset email has been sent successfully', 'success')
        return jsonify(status="success", url=url_for('.users'))
