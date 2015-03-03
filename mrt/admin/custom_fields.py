from flask import render_template
from flask.views import MethodView

from mrt.admin.mixins import PermissionRequiredMixin
from mrt.forms.admin import AdminCustomFieldEditForm
from mrt.models import CustomField
from mrt.common.custom_fields import (
    BaseCustomFieldEdit, BaseCustomFieldUpdatePosition as BaseUpdatePosition)


class CustomFields(PermissionRequiredMixin, MethodView):

    def get(self):
        query = (
            CustomField.query.filter_by(meeting_id=None)
            .order_by(CustomField.sort)
        )
        custom_fields = (
            query.filter_by(custom_field_type=CustomField.PARTICIPANT))
        custom_fields_for_media = (
            query.filter_by(custom_field_type=CustomField.MEDIA))
        return render_template('admin/custom_field/list.html',
                               custom_fields=custom_fields,
                               custom_fields_for_media=custom_fields_for_media)


class CustomFieldEdit(PermissionRequiredMixin, BaseCustomFieldEdit):

    form_class = AdminCustomFieldEditForm
    template = 'admin/custom_field/edit.html'
    meeting_id = None


class CustomFieldUpdatePosition(PermissionRequiredMixin, BaseUpdatePosition):

    meeting_id = None
