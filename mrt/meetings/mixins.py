from flask import g
from flask.ext.login import current_user as user

from mrt.mixins import PermissionRequiredMixin as _PermissionRequiredMixin


class PermissionRequiredMixin(_PermissionRequiredMixin):

    def check_permissions(self):
        perms = self.get_permission_required()
        if user.is_superuser:
            return True
        if g.meeting:
            return (user.staff is g.meeting.owner or
                    user.has_perms(perms, g.meeting.id))
        return bool(user.staff)
