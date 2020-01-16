from flask import flash
from flask import render_template, jsonify
from flask import request, redirect, url_for, abort, Response
from flask.views import MethodView

from mrt.models import db, CustomField


class BaseCustomFieldEdit(MethodView):

    def _get_object(self, custom_field_id=None):
        return (CustomField.query
                .filter_by(meeting_id=self.meeting_id, id=custom_field_id)
                .first_or_404()
                if custom_field_id else None)

    def dispatch_request(self, custom_field_id=None, custom_field_type=None):
        self.obj = self._get_object(custom_field_id)
        return super(BaseCustomFieldEdit, self).dispatch_request(
            custom_field_id=custom_field_id,
            custom_field_type=custom_field_type)

    def get_form_class(self):
        return self.form_class

    def check_dependencies(self):
        return

    def get(self, custom_field_id=None, custom_field_type=None):
        custom_field_type = custom_field_type or self.obj.custom_field_type
        form_class = self.get_form_class()
        form = form_class(obj=self.obj, custom_field_type=custom_field_type)
        return render_template(self.template, form=form, custom_field=self.obj)

    def post(self, custom_field_id=None, custom_field_type=None):
        custom_field_type = custom_field_type or self.obj.custom_field_type
        form_class = self.get_form_class()
        form = form_class(request.form, obj=self.obj,
                          custom_field_type=custom_field_type)
        if form.validate():
            form.save()
            flash('Custom field information saved', 'success')
            return redirect(url_for('.custom_fields'))
        return render_template(self.template, form=form, custom_field=self.obj)

    def delete(self, custom_field_id, custom_field_type=None):
        msg = self.check_dependencies()
        if msg:
            return jsonify(status="error", message=msg)

        if self.obj.is_primary:
            # abort(400)
            return Response(status=400)

        db.session.delete(self.obj)
        db.session.commit()
        flash('Custom field successfully deleted', 'warning')
        return jsonify(status="success", url=url_for('.custom_fields'))


class BaseCustomFieldUpdatePosition(MethodView):

    def post(self):
        items = request.form.getlist('items[]')
        for i, item in enumerate(items):
            custom_field = (CustomField.query
                            .filter_by(id=item, meeting_id=self.meeting_id)
                            .first_or_404())
            custom_field.sort = i
        db.session.commit()
        return jsonify()
