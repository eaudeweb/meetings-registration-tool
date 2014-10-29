from flask import render_template
from flask.ext.login import login_required
from flask.views import MethodView

from mrt.meetings import PermissionRequiredMixin
from mrt.models import User


class Users(PermissionRequiredMixin, MethodView):

    decorators = (login_required,)
    permission_required = ('manage_default', )

    def get(self):
        users = User.query.all()
        return render_template('admin/user/list.html',
                               users=users)
