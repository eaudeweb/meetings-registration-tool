from flask import g
from flask import render_template, flash, make_response, jsonify
from flask import request, redirect, url_for
from flask.views import MethodView

from mrt.forms.meetings import custom_form_factory, custom_object_factory
from mrt.forms.meetings import CustomFieldEditForm
from mrt.models import db
from mrt.models import Participant, CustomField, CustomFieldValue
from mrt.utils import unlink_uploaded_file


class CustomFields(MethodView):

    def get(self):
        custom_fields = CustomField.query.filter_by(meeting_id=g.meeting.id)
        return render_template('meetings/custom_field/list.html',
                               custom_fields=custom_fields)


class CustomFieldEdit(MethodView):

    def _get_object(self, custom_field_id=None):
        return (CustomField.query
                .filter_by(meeting_id=g.meeting.id, id=custom_field_id)
                .first_or_404()
                if custom_field_id else None)

    def get(self, custom_field_id=None):
        custom_field = self._get_object(custom_field_id)
        form = CustomFieldEditForm(obj=custom_field)
        return render_template('meetings/custom_field/edit.html',
                               form=form,
                               custom_field=custom_field)

    def post(self, custom_field_id=None):
        custom_field = self._get_object(custom_field_id)
        form = CustomFieldEditForm(request.form, obj=custom_field)
        if form.validate():
            form.save()
            flash('Custom field information saved', 'success')
            return redirect(url_for('.custom_fields'))
        return render_template('meetings/custom_field/edit.html',
                               form=form,
                               custom_field=custom_field)

    def delete(self, custom_field_id):
        custom_field = self._get_object(custom_field_id)
        db.session.delete(custom_field)
        db.session.commit()
        flash('Custom field successfully deleted', 'warning')
        return jsonify(status="success", url=url_for('.custom_fields'))


class CustomFieldUpload(MethodView):

    def _get_object(self, participant_id):
        return (
            Participant.query
            .filter_by(meeting_id=g.meeting.id, id=participant_id)
            .first_or_404())

    def post(self, participant_id, custom_field_slug):
        participant = self._get_object(participant_id)
        Obj = custom_object_factory(participant, field_type='image')
        Form = custom_form_factory(participant, slug=custom_field_slug)
        form = Form(obj=Obj())
        if form.validate():
            custom_field_value = form.save()[0]
        else:
            return make_response(jsonify(form.errors), 400)

        html = render_template('meetings/custom_field/_image_widget.html',
                               data=custom_field_value.value)
        return jsonify(html=html)

    def delete(self, participant_id, custom_field_slug):
        participant = self._get_object(participant_id)
        custom_field = (
            CustomFieldValue.query
            .filter(CustomFieldValue.participant == participant)
            .filter(CustomFieldValue.custom_field.has(slug=custom_field_slug))
            .first_or_404()
        )
        filename = custom_field.value
        db.session.delete(custom_field)
        db.session.commit()
        unlink_uploaded_file(filename, 'custom')
        # TODO delete thumbnail
        return jsonify()
