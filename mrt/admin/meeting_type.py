from flask import render_template
from flask.views import MethodView
from flask.ext.login import login_required

from mrt.meetings import PermissionRequiredMixin
from mrt.models import MeetingType


class MeetingTypes(PermissionRequiredMixin, MethodView):
    decorators = (login_required, )
    permission_required = ('manage_default', )

    def get(self):
        meeting_types = MeetingType.query
        return render_template('admin/meeting_type/list.html',
                               meeting_types=meeting_types)


class MeetingTypeEdit(PermissionRequiredMixin, MethodView):
    decorators = (login_required, )
    permission_required = ('manage_default', )
