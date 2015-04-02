from flask import current_app as app
from flask import g
from flask import render_template, make_response, jsonify
from flask import request, redirect, url_for
from flask.views import MethodView
from sqlalchemy import not_

from mrt.forms.meetings import custom_form_factory, custom_object_factory
from mrt.forms.meetings import CustomFieldEditForm
from mrt.forms.meetings import ParticipantEditForm, MediaParticipantEditForm
from mrt.meetings.mixins import PermissionRequiredMixin

from mrt.models import db
from mrt.models import Participant, CustomField, CustomFieldValue, Translation

from mrt.utils import crop_file, unlink_participant_custom_file
from mrt.utils import unlink_uploaded_file, rotate_file, unlink_thumbnail_file
from mrt.common.custom_fields import (
    BaseCustomFieldEdit, BaseCustomFieldUpdatePosition as BaseUpdatePosition)


class CustomFields(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting',)
    excluded_fields = ('Country represented', 'Organization represented')

    def get(self):
        query = (
            CustomField.query.filter_by(meeting_id=g.meeting.id)
            .filter(not_(CustomField.label.has(
                Translation.english.in_(self.excluded_fields))))
            .order_by(CustomField.sort))
        custom_fields_for_participants = (
            query.filter_by(custom_field_type=CustomField.PARTICIPANT))

        if g.meeting.media_participant_enabled:
            custom_fields_for_media = (
                query.filter_by(custom_field_type=CustomField.MEDIA))
        else:
            custom_fields_for_media = None

        return render_template(
            'meetings/custom_field/list.html',
            custom_fields_for_participants=custom_fields_for_participants,
            custom_fields_for_media=custom_fields_for_media)


class CustomFieldEdit(PermissionRequiredMixin, BaseCustomFieldEdit):

    permission_required = ('manage_meeting',)
    form_class = CustomFieldEditForm
    template = 'meetings/custom_field/edit.html'

    def __init__(self, *args, **kwargs):
        self.meeting_id = g.meeting.id
        return super(CustomFieldEdit, self).__init__(*args, **kwargs)


class BaseCustomFieldFile(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_participant',)

    def get_object(self, participant_id):
        return (Participant.query.current_meeting()
                .filter_by(id=participant_id)
                .first_or_404())


class CustomFieldUpload(BaseCustomFieldFile):

    def post(self, participant_id, field_slug):
        participant = self.get_object(participant_id)
        cf = CustomField.query.filter_by(slug=field_slug).first_or_404()

        if participant.participant_type == Participant.PARTICIPANT:
            form = ParticipantEditForm
        else:
            form = MediaParticipantEditForm

        field_types = [CustomField.IMAGE]
        Object = custom_object_factory(participant, field_types)
        Form = custom_form_factory(form, field_slugs=[field_slug])
        form = Form(obj=Object())

        if form.validate():
            try:
                form.save(participant)
                data = cf.custom_field_values.first()
            except ValueError:
                data = None
        else:
            return make_response(jsonify(form.errors), 400)

        html = render_template('meetings/custom_field/_image_widget.html',
                               data=data)
        return jsonify(html=html)

    def delete(self, participant_id, field_slug):
        participant = self.get_object(participant_id)
        custom_field = (
            CustomFieldValue.query
            .filter(CustomFieldValue.participant == participant)
            .filter(CustomFieldValue.custom_field.has(slug=field_slug))
            .first_or_404()
        )
        filename = custom_field.value
        db.session.delete(custom_field)
        db.session.commit()
        unlink_participant_custom_file(filename)
        return jsonify()


class CustomFieldRotate(BaseCustomFieldFile):

    def post(self, participant_id, field_slug):
        participant = self.get_object(participant_id)
        custom_field = CustomField.query.filter_by(
            slug=field_slug, field_type='image').first_or_404()
        custom_field_value = CustomFieldValue.query.filter_by(
            participant=participant, custom_field=custom_field
        ).first_or_404()

        newfile = rotate_file(custom_field_value.value, 'custom')
        if newfile == custom_field_value.value:
            return make_response(jsonify(), 400)

        unlink_participant_custom_file(custom_field_value.value)
        custom_field_value.value = newfile
        db.session.commit()

        html = render_template('meetings/custom_field/_image_widget.html',
                               data=custom_field_value.value)
        return jsonify(html=html)


class CustomFieldCropUpload(BaseCustomFieldFile):

    def get(self, participant_id, field_slug):
        participant = self.get_object(participant_id)
        custom_field = CustomField.query.filter_by(
            slug=field_slug, field_type='image').first_or_404()
        custom_field_value = CustomFieldValue.query.filter_by(
            participant=participant, custom_field=custom_field
        ).first_or_404()
        return render_template('meetings/custom_field/crop.html',
                               participant=participant,
                               data=custom_field_value.value)

    def post(self, participant_id, field_slug):
        participant = self.get_object(participant_id)
        custom_field = CustomField.query.filter_by(
            slug=field_slug, field_type='image').first_or_404()
        custom_field_value = CustomFieldValue.query.filter_by(
            participant=participant, custom_field=custom_field
        ).first_or_404()

        form = request.form
        x1 = int(form.get('x1', 0, type=float))
        y1 = int(form.get('y1', 0, type=float))
        x2 = int(form.get('x2', 0, type=float))
        y2 = int(form.get('y2', 0, type=float))

        unlink_uploaded_file(custom_field_value.value, 'crop',
                             dir_name=app.config['PATH_CUSTOM_KEY'])
        unlink_thumbnail_file(custom_field_value.value, dir_name='crops')

        valid_crop = x2 > 0 and y2 > 0
        if valid_crop:
            crop_file(custom_field_value.value, 'custom', (x1, y1, x2, y2))
        if participant.participant_type == Participant.PARTICIPANT:
            url = url_for('.participant_detail', participant_id=participant_id)
        else:
            url = url_for('.media_participant_detail',
                          participant_id=participant_id)
        return redirect(url)


class CustomFieldUpdatePosition(PermissionRequiredMixin, BaseUpdatePosition):

    permission_required = ('manage_meeting', )

    def __init__(self, *args, **kwargs):
        self.meeting_id = g.meeting.id
        return super(CustomFieldUpdatePosition, self).__init__(*args, **kwargs)
