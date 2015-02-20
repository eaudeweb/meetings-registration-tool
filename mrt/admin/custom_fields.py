from flask import flash
from flask import render_template, jsonify
from flask import request, redirect, url_for
from flask.ext.login import login_required
from flask.views import MethodView

from mrt.admin.mixins import PermissionRequiredMixin
from mrt.forms.admin import AdminCustomFieldEditForm
from mrt.models import db, CustomField, CustomFieldValue


class CustomFields(PermissionRequiredMixin, MethodView):

    decorators = (login_required,)

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


class CustomFieldEdit(PermissionRequiredMixin, MethodView):

    decorators = (login_required,)

    def _get_object(self, custom_field_id=None):
        return (CustomField.query
                .filter_by(meeting_id=None, id=custom_field_id)
                .filter_by(is_primary=False)
                .first_or_404()
                if custom_field_id else None)

    def get(self, custom_field_id=None, custom_field_type=None):
        custom_field = self._get_object(custom_field_id)
        custom_field_type = custom_field_type or custom_field.custom_field_type
        form = AdminCustomFieldEditForm(obj=custom_field,
                                        custom_field_type=custom_field_type)
        return render_template('admin/custom_field/edit.html',
                               form=form,
                               custom_field=custom_field)

    def post(self, custom_field_id=None, custom_field_type=None):
        custom_field = self._get_object(custom_field_id)
        custom_field_type = custom_field_type or custom_field.custom_field_type
        form = AdminCustomFieldEditForm(request.form, obj=custom_field,
                                        custom_field_type=custom_field_type)
        if form.validate():
            form.save()
            flash('Custom field information saved', 'success')
            return redirect(url_for('.custom_fields'))
        return render_template('admin/custom_field/edit.html',
                               form=form,
                               custom_field=custom_field)

    def delete(self, custom_field_id):
        custom_field = self._get_object(custom_field_id)
        count = CustomFieldValue.query.filter_by(
            custom_field=custom_field).count()
        if count:
            msg = ("Unable to remove the custom field. There are participants "
                   "with values for this field.")
            return jsonify(status="error", message=msg)

        db.session.delete(custom_field)
        db.session.commit()
        flash('Custom field successfully deleted', 'warning')
        return jsonify(status="success", url=url_for('.custom_fields'))


class CustomFieldUpdatePosition(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', )

    def post(self):
        items = request.form.getlist('items[]')
        for i, item in enumerate(items):
            custom_field = (
                CustomField.query.filter_by(id=item, meeting_id=None)
                .first_or_404())
            custom_field.sort = i
        db.session.commit()
        return jsonify()
