from flask import g
from flask import render_template, flash, make_response, jsonify
from flask import request, redirect, url_for
from flask.views import MethodView

from mrt.forms.meetings import custom_form_factory, custom_object_factory
from mrt.forms.meetings import CustomFieldEditForm
from mrt.models import db
from mrt.models import Participant, CustomField, CustomFieldValue
from mrt.utils import unlink_uploaded_file, rotate_file, unlink_thumbnail_file


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


def _get_participant(participant_id):
    return (
        Participant.query
        .filter_by(meeting_id=g.meeting.id, id=participant_id)
        .first_or_404())


class CustomFieldUpload(MethodView):

    def post(self, participant_id, custom_field_slug):
        participant = _get_participant(participant_id)
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
        participant = _get_participant(participant_id)
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
        unlink_thumbnail_file(filename, 'thumbnail')
        return jsonify()


class CustomFieldRotate(MethodView):

    def post(self, participant_id, custom_field_slug):
        participant = _get_participant(participant_id)
        custom_field = CustomField.query.filter_by(
            slug=custom_field_slug, field_type='image').first_or_404()
        custom_field_value = CustomFieldValue.query.filter_by(
            participant=participant, custom_field=custom_field
        ).first_or_404()

        newfile = rotate_file(custom_field_value.value, 'custom')
        if newfile == custom_field_value.value:
            return make_response(jsonify(), 400)

        custom_field_value.value = newfile
        db.session.commit()

        html = render_template('meetings/custom_field/_image_widget.html',
                               data=custom_field_value.value)
        return jsonify(html=html)


class CustomFieldCropUpload(MethodView):

    def get(self, participant_id, custom_field_slug):
        participant = _get_participant(participant_id)
        custom_field = CustomField.query.filter_by(
            slug=custom_field_slug, field_type='image').first_or_404()
        custom_field_value = CustomFieldValue.query.filter_by(
            participant=participant, custom_field=custom_field
        ).first_or_404()
        return render_template('meetings/custom_field/crop.html',
                               participant=participant,
                               data=custom_field_value.value)

    def post(self, participant_id, custom_field_slug):
        participant = _get_participant(participant_id)
        custom_field = CustomField.query.filter_by(
            slug=custom_field_slug, field_type='image').first_or_404()
        custom_field_value = CustomFieldValue.query.filter_by(
            participant=participant, custom_field=custom_field
        ).first_or_404()

        form = flask.request.form
        x1 = Decimal(form['x1'] or 0) + Decimal(0.1)
        y1 = Decimal(form['y1'] or 0) + Decimal(0.1)
        x2 = Decimal(form['x2'] or 0) + Decimal(0.1)
        y2 = Decimal(form['y2'] or 0) + Decimal(0.1)
        valid_crop = (x2 > Decimal(0.1) and y2 > Decimal(0.1))

        # if valid_crop:


