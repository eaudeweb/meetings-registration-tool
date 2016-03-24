from flask import current_app as app
from flask import g
from flask import render_template, make_response, jsonify
from flask import request, redirect, url_for
from flask.views import MethodView

from mrt.forms.meetings import custom_form_factory, custom_object_factory
from mrt.forms.meetings import (
    CustomFieldPrimaryEditForm, CustomFieldAuxiliaryEditForm,
    CustomFieldProtectedEditForm)
from mrt.forms.meetings import ParticipantEditForm, MediaParticipantEditForm
from mrt.meetings.mixins import PermissionRequiredMixin

from mrt.models import db
from mrt.models import Participant, CustomField, CustomFieldValue, Rule, Meeting

from mrt.utils import crop_file, unlink_participant_custom_file
from mrt.utils import unlink_uploaded_file, rotate_file, unlink_thumbnail_file
from mrt.utils import get_custom_file_as_filestorage
from mrt.common.custom_fields import (
    BaseCustomFieldEdit, BaseCustomFieldUpdatePosition as BaseUpdatePosition)


class CustomFields(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting',)

    def get(self):
        query = (
            CustomField.query.filter_by(meeting_id=g.meeting.id)
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
    template = 'meetings/custom_field/edit.html'

    def __init__(self, *args, **kwargs):
        self.meeting_id = g.meeting.id
        return super(CustomFieldEdit, self).__init__(*args, **kwargs)

    def get_form_class(self):
        if self.obj and self.obj.is_protected:
            return CustomFieldProtectedEditForm
        if self.obj and self.obj.is_primary:
            return CustomFieldPrimaryEditForm
        return CustomFieldAuxiliaryEditForm

    def check_dependencies(self):
        msg = super(CustomFieldEdit, self).check_dependencies()
        if msg:
            return msg

        custom_values = CustomFieldValue.query.filter_by(custom_field=self.obj)
        non_empty_values = custom_values.filter(
            (CustomFieldValue.value != None) & (CustomFieldValue.value != u'')
            | (CustomFieldValue.choice != None))
        if non_empty_values.count():
            return ("Unable to remove the custom field. There are "
                    "participants with values for this field.")

        # Clean up empty values
        custom_values.delete()
        db.session.commit()

        printout_fields = [getattr(self.obj.meeting, field, None)
                           for field in Meeting.PRINTOUT_FIELDS]
        if self.obj in printout_fields:
            return ("This field is currently selected as a printout field")

        count = Rule.get_rules_for_fields([self.obj]).count()
        if count:
            return ("Unable to remove the custom field. There are rules"
                    "defined for this field.")


class BaseCustomFieldFile(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_participant',)

    def get_object(self, participant_id):
        return (Participant.query.current_meeting()
                .filter_by(id=participant_id)
                .first_or_404())

    def get_custom_field(self, participant, field_slug, **kwargs):
        if participant.participant_type == Participant.PARTICIPANT:
            custom_field_type = CustomField.PARTICIPANT
        else:
            custom_field_type = CustomField.MEDIA
        cf = (
            CustomField.query
            .filter_by(slug=field_slug, meeting=g.meeting)
            .filter_by(custom_field_type=custom_field_type))
        if kwargs:
            cf = cf.filter_by(**kwargs)
        return cf.first_or_404()

    def get_custom_field_value(self, cf, participant):
        return (cf.custom_field_values
               .filter_by(participant=participant)
               .first_or_404())


class CustomFieldUpload(BaseCustomFieldFile):

    def post(self, participant_id, field_slug):
        participant = self.get_object(participant_id)
        cf = self.get_custom_field(participant, field_slug)

        if participant.participant_type == Participant.PARTICIPANT:
            form_class = ParticipantEditForm
            g.rule_type = Rule.PARTICIPANT
        else:
            form_class = MediaParticipantEditForm
            g.rule_type = Rule.MEDIA

        field_types = [CustomField.IMAGE]
        Object = custom_object_factory(participant, field_types)
        Form = custom_form_factory(form_class, field_slugs=[field_slug])
        form = Form(obj=Object())

        if form.validate():
            form.save(participant)
            cfv = (cf.custom_field_values.filter_by(participant=participant)
                   .scalar())
            if cfv:
                data = get_custom_file_as_filestorage(cfv.value)
            else:
                data = {}
        else:
            return make_response(jsonify(form.errors), 400)

        html = render_template('meetings/custom_field/_image_widget.html',
                               data=data)
        return jsonify(html=html)

    def delete(self, participant_id, field_slug):
        participant = self.get_object(participant_id)
        cf = self.get_custom_field(participant, field_slug)
        cfv = self.get_custom_field_value(cf, participant)

        filename = cfv.value
        db.session.delete(cfv)
        db.session.commit()
        unlink_participant_custom_file(filename)
        return jsonify()


class CustomFieldRotate(BaseCustomFieldFile):

    def post(self, participant_id, field_slug):
        participant = self.get_object(participant_id)
        cf = self.get_custom_field(participant, field_slug,
                                   field_type='image')
        cfv = self.get_custom_field_value(cf, participant)

        newfile = rotate_file(cfv.value, 'custom')
        if newfile == cfv.value:
            return make_response(jsonify(), 400)

        unlink_participant_custom_file(cfv.value)
        cfv.value = newfile
        db.session.commit()

        data = get_custom_file_as_filestorage(newfile)
        html = render_template('meetings/custom_field/_image_widget.html',
                               data=data)
        return jsonify(html=html)


class CustomFieldCropUpload(BaseCustomFieldFile):

    def get(self, participant_id, field_slug):
        participant = self.get_object(participant_id)
        cf = self.get_custom_field(participant, field_slug,
                                   field_type='image')
        cfv = self.get_custom_field_value(cf, participant)
        return render_template('meetings/custom_field/crop.html',
                               participant=participant,
                               data=cfv.value)

    def post(self, participant_id, field_slug):
        participant = self.get_object(participant_id)
        cf = self.get_custom_field(participant, field_slug,
                                   field_type='image')
        cfv = self.get_custom_field_value(cf, participant)

        form = request.form
        x1 = int(form.get('x1', 0, type=float))
        y1 = int(form.get('y1', 0, type=float))
        x2 = int(form.get('x2', 0, type=float))
        y2 = int(form.get('y2', 0, type=float))

        unlink_uploaded_file(cfv.value, 'crop',
                             dir_name=app.config['PATH_CUSTOM_KEY'])
        unlink_thumbnail_file(cfv.value, dir_name='crops')

        valid_crop = x2 > 0 and y2 > 0
        if valid_crop:
            crop_file(cfv.value, 'custom', (x1, y1, x2, y2))
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
