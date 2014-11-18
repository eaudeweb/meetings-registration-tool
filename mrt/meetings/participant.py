from functools import wraps

from werkzeug.utils import HTMLBuilder
from flask import g, request, redirect, url_for, jsonify, json
from flask import render_template, flash, Response
from flask.views import MethodView
from flask.ext.login import current_user as user

from mrt.forms.meetings import custom_form_factory, custom_object_factory
from mrt.forms.meetings import ParticipantDummyForm, ParticipantEditForm
from mrt.forms.meetings import AcknowledgeEmailForm

from mrt.meetings import PermissionRequiredMixin
from mrt.mixins import FilterView

from mrt.mail import send_single_message
from mrt.models import db, Participant, CustomField, Staff, Category
from mrt.models import Phrase
from mrt.models import search_for_participant, get_participants_full

from mrt.pdf import render_pdf
from mrt.signals import activity_signal, notification_signal
from mrt.utils import generate_excel, set_language


def _category_required(func):
    @wraps(func)
    def wrapper(**kwargs):
        query = Category.query.filter_by(meeting=g.meeting)
        if (query.count() == 0):
            return render_template('meetings/category_required.html')
        return func(**kwargs)
    return wrapper


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

    def process_attended(self, participant, val):
        return '<span class="glyphicon glyphicon-ok"></span>' if val else ''

    def process_verified(self, participant, val):
        return '<span class="glyphicon glyphicon-ok"></span>' if val else ''

    def process_credentials(self, participant, val):
        return '<span class="glyphicon glyphicon-ok"></span>' if val else ''

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
            .active().first_or_404())
        field_types = [CustomField.TEXT, CustomField.SELECT,
                       CustomField.COUNTRY, CustomField.CATEGORY]
        Form = custom_form_factory(field_types=field_types)
        Object = custom_object_factory(participant, field_types)
        form = Form(obj=Object())

        field_types = [CustomField.CHECKBOX]
        FlagsForm = custom_form_factory(field_types=field_types)
        FlagsObject = custom_object_factory(participant, field_types)
        flags_form = FlagsForm(obj=FlagsObject())

        field_types = [CustomField.IMAGE]
        ImagesForm = custom_form_factory(field_types=field_types)
        ImagesObject = custom_object_factory(participant, field_types)
        images_form = ImagesForm(obj=ImagesObject())

        return render_template('meetings/participant/detail.html',
                               participant=participant,
                               form=form,
                               flags_form=flags_form,
                               images_form=images_form)


class DefaultParticipantDetail(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_default', )

    def get(self, participant_id):
        participant = (
            Participant.query
            .filter_by(meeting_id=g.meeting.id, id=participant_id)
            .active().first_or_404())
        field_types = [CustomField.TEXT, CustomField.SELECT,
                       CustomField.COUNTRY]
        Form = custom_form_factory(field_types=field_types)
        Object = custom_object_factory(participant, field_types)
        form = Form(obj=Object())

        field_types = [CustomField.CHECKBOX]
        FlagsForm = custom_form_factory(field_types=field_types)
        FlagsObject = custom_object_factory(participant, field_types)
        flags_form = FlagsForm(obj=FlagsObject())

        field_types = [CustomField.IMAGE]
        ImagesForm = custom_form_factory(field_types=field_types)
        ImagesObject = custom_object_factory(participant, field_types)
        images_form = ImagesForm(obj=ImagesObject())

        return render_template('meetings/participant/detail.html',
                               participant=participant,
                               form=form,
                               flags_form=flags_form,
                               images_form=images_form)


class ParticipantEdit(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_participant',)
    decorators = (_category_required,)

    def _get_object(self, participant_id=None):
        return (Participant.query
                .filter_by(meeting_id=g.meeting.id, id=participant_id)
                .active()
                .first_or_404()
                if participant_id else None)

    def get(self, participant_id=None):
        participant = self._get_object(participant_id)
        field_types = [CustomField.TEXT, CustomField.SELECT,
                       CustomField.COUNTRY, CustomField.CATEGORY]
        Form = custom_form_factory(field_types=field_types)
        Object = custom_object_factory(participant, field_types)
        form = Form(obj=Object())

        field_types = [CustomField.CHECKBOX]
        FlagsForm = custom_form_factory(field_types=field_types)
        FlagsObject = custom_object_factory(participant, field_types)
        flags_form = FlagsForm(obj=FlagsObject())

        return render_template('meetings/participant/edit.html',
                               form=form,
                               flags_form=flags_form,
                               participant=participant)

    def post(self, participant_id=None):
        participant = self._get_object(participant_id)
        field_types = [CustomField.TEXT, CustomField.SELECT,
                       CustomField.COUNTRY, CustomField.CATEGORY]
        Form = custom_form_factory(field_types=field_types,
                                   form=ParticipantEditForm)
        Object = custom_object_factory(participant, field_types)
        form = Form(obj=Object())

        field_types = [CustomField.CHECKBOX]
        FlagsForm = custom_form_factory(field_types=field_types)
        FlagsObject = custom_object_factory(participant, field_types)
        flags_form = FlagsForm(obj=FlagsObject())
        if (form.validate() and flags_form.validate()):
            participant = form.save(participant)
            flags_form.save(participant)
            flash('Person information saved', 'success')
            staff = Staff.query.filter_by(user=user).first()
            if participant_id:
                activity_signal.send(self, participant=participant,
                                     action='edit', staff=staff)
                url = url_for('.participant_detail',
                              participant_id=participant.id)
            else:
                activity_signal.send(self, participant=participant,
                                     action='add', staff=staff)
                notification_signal.send(self, participant=participant)
                url = url_for('.participants')
            return redirect(url)

        return render_template('meetings/participant/edit.html',
                               form=form,
                               flags_form=flags_form,
                               participant=participant)

    def delete(self, participant_id):
        participant = self._get_object(participant_id)
        participant.deleted = True
        staff = Staff.query.filter_by(user=user).first()
        activity_signal.send(self, participant=participant,
                             action='delete', staff=staff)
        db.session.commit()
        flash('Participant successfully deleted', 'warning')
        return jsonify(status="success", url=url_for('.participants'))


class DefaultParticipantEdit(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_participant',)

    def _get_object(self, participant_id=None):
        return (Participant.query
                .filter_by(meeting_id=g.meeting.id, id=participant_id)
                .active()
                .first_or_404()
                if participant_id else None)

    def get(self, participant_id=None):
        participant = self._get_object(participant_id)
        field_types = [CustomField.TEXT, CustomField.SELECT,
                       CustomField.COUNTRY]
        Form = custom_form_factory(field_types=field_types)
        Object = custom_object_factory(participant, field_types)
        form = Form(obj=Object())

        field_types = [CustomField.CHECKBOX]
        FlagsForm = custom_form_factory(field_types=field_types)
        FlagsObject = custom_object_factory(participant, field_types)
        flags_form = FlagsForm(obj=FlagsObject())

        return render_template('meetings/participant/edit.html',
                               form=form,
                               flags_form=flags_form,
                               participant=participant)

    def post(self, participant_id=None):
        participant = self._get_object(participant_id)
        field_types = [CustomField.TEXT, CustomField.SELECT,
                       CustomField.COUNTRY]
        Form = custom_form_factory(field_types=field_types,
                                   form=ParticipantEditForm)
        Object = custom_object_factory(participant, field_types)
        form = Form(obj=Object())

        field_types = [CustomField.CHECKBOX]
        FlagsForm = custom_form_factory(field_types=field_types)
        FlagsObject = custom_object_factory(participant, field_types)
        flags_form = FlagsForm(obj=FlagsObject())
        if (form.validate() and flags_form.validate()):
            participant = form.save(participant)
            flags_form.save(participant)
            flash('Person information saved', 'success')
            staff = Staff.query.filter_by(user=user).first()
            if participant_id:
                activity_signal.send(self, participant=participant,
                                     action='edit', staff=staff)
                url = url_for('.default_participant_detail',
                              participant_id=participant.id)
            return redirect(url)

        return render_template('meetings/participant/edit.html',
                               form=form,
                               flags_form=flags_form,
                               participant=participant)


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
        context = {'participant': participant, 'nostripe': nostripe}
        return render_pdf('meetings/participant/badge.html',
                          width='3.4in', height='2.15in',
                          footer=False, orientation='portrait',
                          context=context)


class ParticipantLabel(PermissionRequiredMixin, MethodView):

    permission_required = ('view_participant', )

    def get(self, participant_id):
        participant = Participant.query.filter_by(
            meeting_id=g.meeting.id, id=participant_id).active().first_or_404()
        context = {'participant': participant}
        return render_pdf('meetings/participant/label.html',
                          height="8.3in", width="11.7in",
                          orientation="landscape", footer=False,
                          context=context)


class ParticipantEnvelope(PermissionRequiredMixin, MethodView):

    permission_required = ('view_participant', )

    def get(self, participant_id):
        participant = Participant.query.filter_by(
            meeting_id=g.meeting.id, id=participant_id).active().first_or_404()
        context = {'participant': participant}
        return render_pdf('meetings/participant/envelope.html',
                          height='6.4in', width='9.0in',
                          orientation="portrait", footer=False,
                          context=context)


class ParticipantAcknowledgeEmail(PermissionRequiredMixin, MethodView):

    template_name = 'meetings/participant/acknowledge.html'
    permission_required = ('view_participant', )

    def get_participant(self, participant_id):
        return (
            Participant.query
            .filter_by(meeting=g.meeting, id=participant_id).active()
            .first_or_404())

    def get(self, participant_id):
        participant = self.get_participant(participant_id)
        subject = Phrase.query.filter_by(meeting=g.meeting,
                                         group=Phrase.ACK_EMAIL,
                                         name=Phrase.SUBJECT).scalar()
        body = Phrase.query.filter_by(meeting=g.meeting,
                                      group=Phrase.ACK_EMAIL,
                                      name=Phrase.BODY).scalar()
        form = AcknowledgeEmailForm(to=participant.email)
        language = getattr(participant, 'lang', 'english')
        if subject:
            form.subject.data = getattr(subject.description,
                                        language, None)
        if body:
            form.message.data = getattr(body.description,
                                        language, None)
        set_language(language)
        return render_template(self.template_name, participant=participant,
                               form=form, language=language)

    def post(self, participant_id):
        participant = self.get_participant(participant_id)
        form = AcknowledgeEmailForm(request.form)
        if form.validate():
            context = {
                'participant': participant,
                'template': 'meetings/printouts/acknowledge_detail.html'}
            attachement = render_pdf('meetings/printouts/printout.html',
                                     height='11.7in',
                                     width='8.26in',
                                     orientation='portrait',
                                     as_attachement=True,
                                     context=context)
            if send_single_message(form.to.data, form.subject.data,
                                   form.message.data,
                                   attachement=attachement,
                                   attachement_name='registration_detail.pdf'):
                flash('Message successfully sent', 'success')
                return redirect(
                    url_for('.participant_detail',
                            participant_id=participant.id)
                )
            else:
                flash('Message failed to send', 'error')

        set_language(participant.lang)
        return render_template(self.template_name, participant=participant,
                               form=form)


class ParticipantAcknowledgePDF(MethodView):

    def get(self, participant_id):
        participant = Participant.query.filter_by(
            meeting_id=g.meeting.id, id=participant_id).active().first_or_404()
        context = {'participant': participant}
        language = getattr(participant, 'lang', 'english')
        set_language(language)
        return render_pdf('meetings/printouts/acknowledge_detail.html',
                          height='11.7in', width='8.26in',
                          orientation='portrait', footer=False,
                          context=context)


class ParticipantsExport(PermissionRequiredMixin, MethodView):

    permission_required = ('view_participant', )

    def get(self):

        participants = get_participants_full(g.meeting.id)

        #TODO Add the rest of the necessary fields
        columns = [
            'title', 'first_name', 'last_name', 'country', 'email',
            'language'
        ]

        custom_fields = g.meeting.custom_fields.filter_by(is_primary=True)
        cfs = [cf.slug for cf in custom_fields
               if cf.field_type.code not in ('image',)]
        form = ParticipantDummyForm()
        header = [str(form._fields[k].label.text) for k in columns]
        header.extend([cf.title() for cf in cfs])
        columns += cfs
        rows = []
        for p in participants:
            data = {}
            data['title'] = p.title.value
            data['first_name'] = p.first_name
            data['last_name'] = p.last_name
            data['country'] = p.country.name
            data['email'] = p.email
            data['language'] = p.language.value
            data['category_id'] = p.category_id
            data['represented_country'] = p.represented_country.name
            data['represented_region'] = (
                p.represented_region.value if p.represented_region else None)
            data['represented_organization'] = p.represented_organization
            data['attended'] = 'Yes' if p.attended == 'true' else None
            data['verified'] = 'Yes' if p.verified == 'true' else None
            data['credentials'] = 'Yes' if p.credentials == 'true' else None

            rows.append([data.get(k) or '' for k in columns])

        return Response(
            generate_excel(header, rows),
            mimetype='application/vnd.ms-excel',
            headers={'Content-Disposition': 'attachment; filename=%s.sls'
                     % 'registration'})
