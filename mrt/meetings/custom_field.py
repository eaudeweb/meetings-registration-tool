from flask import g
from flask import request, redirect, url_for
from flask import render_template, flash
from flask.views import MethodView

from mrt.models import CustomField
from mrt.forms.meetings import CustomFieldEditForm


class CustomFields(MethodView):

    def get(self):
        custom_fields = CustomField.query.filter_by(meeting_id=g.meeting.id)
        return render_template('meetings/custom_field/list.html',
                               custom_fields=custom_fields)


class CustomFieldEdit(MethodView):

    def _get_object(self, custom_field_slug=None):
        return (CustomField.query
                .filter_by(meeting_id=g.meeting.id, slug=custom_field_slug)
                .first_or_404()
                if custom_field_slug else None)

    def get(self, custom_field_slug=None):
        custom_field = self._get_object(custom_field_slug)
        form = CustomFieldEditForm(obj=custom_field)
        return render_template('meetings/custom_field/edit.html',
                               form=form)

    def post(self, custom_field_slug=None):
        custom_field = self._get_object(custom_field_slug)
        form = CustomFieldEditForm(request.form, obj=custom_field)
        if form.validate():
            form.save()
            flash('Custom field information saved', 'success')
            return redirect(url_for('.custom_fields'))
        return render_template('meetings/custom_field/edit.html',
                               form=form)
