from flask import render_template, jsonify
from flask.ext.login import login_required
from flask.views import MethodView

from mrt.meetings import PermissionRequiredMixin
from mrt.models import User, db


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
        user.active = not user.active
        db.session.commit()
        return jsonify(status="success")
