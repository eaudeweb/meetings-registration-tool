from flask import g
from flask.ext.login import current_user as user

from mrt.mixins import PermissionRequiredMixin as _PermissionRequiredMixin


class PermissionRequiredMixin(_PermissionRequiredMixin):

    def check_permissions(self):
        perms = self.get_permission_required()
        admin_perms = [x.replace('view', 'manage', 1) for x in perms]
        if user.is_superuser:
            return True
        return (
            user.staff and user.staff is g.meeting.owner or
            user.has_perms(perms, meeting_id=g.meeting.id) or
            user.has_perms(admin_perms, meeting_id=g.meeting.id)
        )
