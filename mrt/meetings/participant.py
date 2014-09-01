from werkzeug.utils import HTMLBuilder

from flask import current_app as app
from flask import g, request, redirect, url_for, jsonify, json
from flask import render_template, flash, Response
from flask.views import MethodView

from mrt.forms.meetings import custom_form_factory, custom_object_factory
from mrt.forms.meetings import ParticipantEditForm
from mrt.meetings import PermissionRequiredMixin
from mrt.mixins import FilterView
from mrt.models import db, Participant, search_for_participant
from mrt.pdf import render_pdf
from mrt.signals import activity_signal, notification_signal
from mrt.utils import generate_excel


class Participants(PermissionRequiredMixin, MethodView):

    permission_required = ('view_participant', )

    def get(self):
        return render_template('meetings/participant/list.html')


class ParticipantsFilter(PermissionRequiredMixin, MethodView, FilterView):

    permission_required = ('view_participant', )

    def process_last_name(self, participant, val):
        html = HTMLBuilder('html')
        url = url_for('.participant_detail', participant_id=participant.id)
        return html.a(participant.name, href=url)

    def process_category_id(self, participant, val):
        return str(participant.category)

    def get_queryset(self, **opt):
        participants = (
            Participant.query.filter_by(meeting_id=g.meeting.id).active())
        total = participants.count()

        for item in opt['order']:
            participants = participants.order_by(
                '%s %s' % (item['column'], item['dir']))

        if opt['search']:
            participants = search_for_participant(opt['search'], participants)

        participants = participants.limit(opt['limit']).offset(opt['start'])
        return participants, total


class ParticipantSearch(PermissionRequiredMixin, MethodView):

    permission_required = ('view_participant', )

    def get(self):
        participants = search_for_participant(request.args['search'])
        results = []
        for p in participants:
            results.append({
                'value': p.name,
                'url': url_for('.participant_detail', participant_id=p.id)
            })
        return json.dumps(results)


class ParticipantDetail(PermissionRequiredMixin, MethodView):

    permission_required = ('view_participant', )

    def get(self, participant_id):
        participant = (
            Participant.query
            .filter_by(meeting_id=g.meeting.id, id=participant_id)
            .active()
            .first_or_404())
        form = ParticipantEditForm(obj=participant)

        CustomFormImages = custom_form_factory(participant, field_type='image')
        CustomObjectImages = custom_object_factory(participant,
                                                   field_type='image')
        custom_form_images = CustomFormImages(obj=CustomObjectImages())

        CustomFormText = custom_form_factory(participant, field_type='text')
        CustomObjectText = custom_object_factory(participant,
                                                 field_type='text')
        custom_form_text = CustomFormText(obj=CustomObjectText())

        CustomFormCheckbox = custom_form_factory(participant,
                                                 field_type='checkbox')
        CustomObjectCheckbox = custom_object_factory(participant,
                                                     field_type='checkbox')
        custom_form_checkbox = CustomFormCheckbox(obj=CustomObjectCheckbox())

        return render_template('meetings/participant/detail.html',
                               participant=participant,
                               custom_form_images=custom_form_images,
                               custom_form_text=custom_form_text,
                               custom_form_checkbox=custom_form_checkbox,
                               form=form)


class ParticipantEdit(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_participant', )

    def _get_object(self, participant_id=None):
        return (Participant.query
                .filter_by(meeting_id=g.meeting.id, id=participant_id)
                .active()
                .first_or_404()
                if participant_id else None)

    def get(self, participant_id=None):
        participant = self._get_object(participant_id)
        form = ParticipantEditForm(obj=participant)
        CustomFormText = custom_form_factory(participant, field_type='text')
        CustomObjectText = custom_object_factory(participant,
                                                 field_type='text')
        custom_form_text = CustomFormText(obj=CustomObjectText())

        CustomFormCheckbox = custom_form_factory(participant,
                                                 field_type='checkbox')
        CustomObjectCheckbox = custom_object_factory(participant,
                                                     field_type='checkbox')
        custom_form_checkbox = CustomFormCheckbox(obj=CustomObjectCheckbox())

        return render_template('meetings/participant/edit.html',
                               form=form,
                               custom_form_text=custom_form_text,
                               custom_form_checkbox=custom_form_checkbox,
                               participant=participant)

    def post(self, participant_id=None):
        participant = self._get_object(participant_id)
        form = ParticipantEditForm(request.form, obj=participant)
        CustomFormText = custom_form_factory(participant, field_type='text')
        CustomObjectText = custom_object_factory(participant,
                                                 field_type='text')
        custom_form_text = CustomFormText(obj=CustomObjectText())

        CustomFormCheckbox = custom_form_factory(participant,
                                                 field_type='checkbox')
        CustomObjectCheckbox = custom_object_factory(participant,
                                                     field_type='checkbox')
        custom_form_checkbox = CustomFormCheckbox(obj=CustomObjectCheckbox())

        if (form.validate() and custom_form_text.validate() and
           custom_form_checkbox.validate()):
            participant = form.save()
            custom_form_text.save(participant)
            custom_form_checkbox.save(participant)
            flash('Person information saved', 'success')
            if participant_id:
                activity_signal.send(self, participant=participant,
                                     action='edit')
            else:
                activity_signal.send(self, participant=participant,
                                     action='add')
                notification_signal.send(self, participant=participant)
            if participant:
                url = url_for('.participant_detail',
                              participant_id=participant.id)
            else:
                url = url_for('.participants')
            return redirect(url)
        return render_template('meetings/participant/edit.html',
                               form=form,
                               custom_form_text=custom_form_text,
                               participant=participant)

    def delete(self, participant_id):
        participant = self._get_object(participant_id)
        participant.deleted = True
        activity_signal.send(self, participant=participant,
                             action='delete')
        db.session.commit()
        flash('Participant successfully deleted', 'warning')
        return jsonify(status="success", url=url_for('.participants'))


class ParticipantRestore(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_participant',)

    def post(self, participant_id):
        participant = (
            Participant.query
            .filter_by(meeting_id=g.meeting.id, id=participant_id)
            .first_or_404())
        participant.deleted = False
        activity_signal.send(self, participant=participant,
                             action='restore')
        db.session.commit()
        flash('Participant successfully restored', 'success')
        return jsonify(status="success", url=url_for('.participant_detail',
                       participant_id=participant.id))


class ParticipantBadge(PermissionRequiredMixin, MethodView):

    permission_required = ('view_participant', )

    def get(self, participant_id):
        participant = (
            Participant.query.filter_by(meeting_id=g.meeting.id,
                                        id=participant_id)
            .active()
            .first_or_404())
        nostripe = request.args.get('nostripe')
        return render_pdf('meetings/participant/badge.html',
                          participant=participant,
                          nostripe=nostripe,
                          width='3.4in',
                          height='2.15in',
                          orientation='portrait')


class ParticipantLabel(PermissionRequiredMixin, MethodView):

    permission_required = ('view_participant', )

    def get(self, participant_id):
        participant = Participant.query.filter_by(
            meeting_id=g.meeting.id, id=participant_id).active().first_or_404()
        return render_pdf('meetings/participant/label.html',
                          height="8.3in",
                          width="11.7in",
                          orientation="landscape",
                          participant=participant)


class ParticipantEnvelope(PermissionRequiredMixin, MethodView):

    permission_required = ('view_participant', )

    def get(self, participant_id):
        participant = Participant.query.filter_by(
            meeting_id=g.meeting.id, id=participant_id).active().first_or_404()
        product_logo = (app.config['UPLOADED_LOGOS_DEST'] /
                        app.config['PRODUCT_LOGO'])
        product_side_logo = (app.config['UPLOADED_LOGOS_DEST'] /
                             app.config['PRODUCT_SIDE_LOGO'])
        return render_pdf('meetings/participant/envelope.html',
                          product_logo=product_logo,
                          product_side_logo=product_side_logo,
                          height='6.4in',
                          width='9.0in',
                          orientation="portrait",
                          participant=participant)


class ParticipantsExport(PermissionRequiredMixin, MethodView):

    permission_required = ('view_participant', )

    def get(self):

        participants = (
            Participant.query.filter_by(meeting_id=g.meeting.id).active())

        #TODO Add the rest of the necessary fields
        columns = [
            'title', 'first_name', 'last_name', 'country', 'email',
            'language'
        ]

        form = ParticipantEditForm()

        header = [str(form._fields[k].label.text) for k in columns]

        rows = []
        for p in participants:
            data = {}
            data['title'] = p.title.value
            data['first_name'] = p.first_name
            data['last_name'] = p.last_name
            data['country'] = p.country.name
            data['email'] = p.email
            data['language'] = p.language.value

            rows.append([data.get(k) or '' for k in columns])

        return Response(
            generate_excel(header, rows),
            mimetype='application/vnd.ms-excel',
            headers={'Content-Disposition': 'attachment; filename=%s.sls'
                     % 'registration'})
