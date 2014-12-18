from flask.ext.login import current_user as user
from mrt.mixins import PermissionRequiredMixin as _PermissionRequiredMixin


class PermissionRequiredMixin(_PermissionRequiredMixin):

    def check_permissions(self):
        return user.is_superuser
