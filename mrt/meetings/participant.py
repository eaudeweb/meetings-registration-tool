from functools import wraps

from werkzeug.utils import HTMLBuilder
from flask import g, request, redirect, url_for, jsonify, json
from flask import render_template, flash, Response
from flask.views import MethodView
from flask.ext.login import current_user as user

from mrt.forms.meetings import custom_form_factory, custom_object_factory
from mrt.forms.meetings import ParticipantDummyForm, ParticipantEditForm
from mrt.forms.meetings import MediaParticipantEditForm
from mrt.forms.meetings import AcknowledgeEmailForm

from mrt.meetings import PermissionRequiredMixin
from mrt.mixins import FilterView

from mrt.mail import send_single_message
from mrt.models import db, Participant, CustomField, Category, Phrase
from mrt.models import search_for_participant, get_participants_full

from mrt.pdf import PdfRenderer
from mrt.signals import activity_signal
from mrt.utils import generate_excel, set_language


def _check_category(category_type):
    query = (Category.query.filter_by(meeting=g.meeting)
             .filter_by(category_type=Category.PARTICIPANT))
    if query.count() == 0:
        return render_template('meetings/category_required.html')


def _participant_category_required(func):
    @wraps(func)
    def wrapper(**kwargs):
        _check_category(Category.PARTICIPANT)
        return func(**kwargs)
    return wrapper


def _media_participant_category_required(func):
    @wraps(func)
    def wrapper(**kwargs):
        _check_category(Category.MEDIA)
        return func(**kwargs)
    return wrapper


class Participants(PermissionRequiredMixin, MethodView):

    permission_required = ('view_participant', )

    def get(self):
        return render_template('meetings/participant/participant/list.html')


class MediaParticipants(PermissionRequiredMixin, MethodView):

    permission_required = ('view_media_participant',)

    def get(self):
        return render_template('meetings/participant/media/list.html')


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
        participants = Participant.query.current_meeting().participants()
        total = participants.count()

        for item in opt['order']:
            participants = participants.order_by(
                '%s %s' % (item['column'], item['dir']))

        if opt['search']:
            participants = search_for_participant(opt['search'], participants)
        participants = participants.limit(opt['limit']).offset(opt['start'])
        return participants, total


class MediaParticipantsFilter(PermissionRequiredMixin, MethodView, FilterView):

    permission_required = ('view_media_participant',)

    def process_last_name(self, participant, val):
        html = HTMLBuilder('html')
        url = url_for('.media_participant_detail',
                      participant_id=participant.id)
        return html.a(participant.name, href=url)

    def process_category_id(self, participant, val):
        return str(participant.category)

    def get_queryset(self, **opt):
        participants = Participant.query.current_meeting().media_participants()
        total = participants.count()

        for item in opt['order']:
            participants = participants.order_by(
                '%s %s' % (item['column'], item['dir']))

        if opt['search']:
            participants = (
                participants.filter(
                    Participant.first_name.contains(opt['search']) |
                    Participant.last_name.contains(opt['search']) |
                    Participant.email.contains(opt['search'])
                )
            )

        participants = (
            participants.limit(opt['limit']).offset(opt['start']))
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


class BaseParticipantDetail(PermissionRequiredMixin, MethodView):

    def _get_queryset(self):
        raise NotImplemented

    def get(self, participant_id):
        participant = self._get_queryset(participant_id)
        Form = custom_form_factory(self.form_class)
        Object = custom_object_factory(participant)
        form = Form(obj=Object())
        return render_template(self.template, participant=participant,
                               form=form)


class ParticipantDetail(BaseParticipantDetail):

    permission_required = ('view_participant',)
    form_class = ParticipantEditForm
    template = 'meetings/participant/participant/detail.html'

    def _get_queryset(self, participant_id):
        return (Participant.query.current_meeting().participants()
                .filter_by(id=participant_id)
                .first_or_404())


class MediaParticipantDetail(BaseParticipantDetail):

    permission_required = ('view_media_participant',)
    form_class = MediaParticipantEditForm
    template = 'meetings/participant/media/detail.html'

    def _get_queryset(self, participant_id):
        return (Participant.query.current_meeting().media_participants()
                .filter_by(id=participant_id)
                .first_or_404())


class DefaultParticipantDetail(BaseParticipantDetail):

    permission_required = ('manage_default',)
    form_class = ParticipantEditForm
    template = 'meetings/participant/default/participant_detail.html'

    def _get_queryset(self, participant_id):
        return (Participant.query.current_meeting().default_participants()
                .filter_by(id=participant_id)
                .first_or_404())


class DefaultMediaParticipantDetail(BaseParticipantDetail):

    permission_required = ('manage_default',)
    form_class = MediaParticipantEditForm
    template = 'meetings/participant/default/media_detail.html'

    def _get_queryset(self, participant_id):
        return (Participant.query.current_meeting()
                .default_media_participants()
                .filter_by(id=participant_id)
                .first_or_404())


class BaseParticipantEdit(PermissionRequiredMixin, MethodView):

    def get_object(self):
        raise NotImplemented

    def get_success_url(self):
        raise NotImplemented

    def _edit_signals(self, participant, is_created):
        if is_created:
            activity_signal.send(self, participant=participant,
                                 action='edit', staff=user.staff)
        else:
            activity_signal.send(self, participant=participant,
                                 action='add', staff=user.staff)

    def _delete_signals(self, participant):
        activity_signal.send(self, participant=participant,
                             action='delete', staff=user.staff)

    def get_form(self):
        return custom_form_factory(self.form_class,
                                   excluded_field_types=[CustomField.IMAGE])

    def get(self, participant_id=None):
        participant = self.get_object(participant_id)
        Form = self.get_form()
        Object = custom_object_factory(participant)
        form = Form(obj=Object())
        return render_template(self.template, form=form,
                               participant=participant)

    def post(self, participant_id=None):
        participant = self.get_object(participant_id)
        Form = self.get_form()
        Object = custom_object_factory(participant)
        form = Form(obj=Object())
        if form.validate():
            participant = form.save(participant)
            flash('Person information saved', 'success')
            is_created = True if participant_id else False
            self._edit_signals(participant, is_created)
            return redirect(self.get_success_url(participant))
        return render_template(self.template, form=form,
                               participant=participant)

    def delete(self, participant_id):
        participant = self.get_object(participant_id)
        participant.deleted = True
        db.session.commit()
        self._delete_signals(participant)
        flash('Participant successfully deleted', 'warning')
        return jsonify(status='success', url=self.get_success_url())


class ParticipantEdit(BaseParticipantEdit):

    permission_required = ('manage_participant',)
    decorators = (_participant_category_required,)
    template = 'meetings/participant/participant/edit.html'
    form_class = ParticipantEditForm

    def get_object(self, participant_id=None):
        return (Participant.query.current_meeting().participants()
                .filter_by(id=participant_id)
                .first_or_404() if participant_id else None)

    def get_success_url(self, participant=None):
        if participant:
            url = url_for('.participant_detail',
                          participant_id=participant.id)
        else:
            url = url_for('.participants')
        return url


class MediaParticipantEdit(ParticipantEdit):

    permission_required = ('manage_media_participant',)
    decorators = (_media_participant_category_required,)
    template = 'meetings/participant/media/edit.html'
    form_class = MediaParticipantEditForm

    def get_object(self, participant_id=None):
        return (
            Participant.query.current_meeting().media_participants()
            .filter_by(id=participant_id)
            .first_or_404()
            if participant_id else None)

    def get_success_url(self, participant=None):
        if participant:
            url = url_for('.media_participant_detail',
                          participant_id=participant.id)
        else:
            url = url_for('.media_participants')
        return url


class DefaultParticipantEdit(BaseParticipantEdit):

    permission_required = ('manage_participant',)
    template = 'meetings/participant/default/edit.html'
    form_class = ParticipantEditForm

    def get_form(self):
        return custom_form_factory(self.form_class,
                                   excluded_field_types=[CustomField.IMAGE,
                                                         CustomField.CATEGORY])

    def get_object(self, participant_id):
        return (Participant.query.current_meeting().default_participants()
                .filter_by(id=participant_id)
                .first_or_404())

    def get_success_url(self, participant):
        return url_for('.default_participant_detail',
                       participant_id=participant.id)


class DefaultMediaParticipantEdit(DefaultParticipantEdit):

    permission_required = ('manage_participant',)
    template = 'meetings/participant/default/edit.html'
    form_class = MediaParticipantEditForm

    def get_object(self, participant_id):
        return (Participant.query.current_meeting()
                .default_media_participants()
                .filter_by(id=participant_id)
                .first_or_404())

    def get_success_url(self, participant):
        return url_for('.default_media_participant_detail',
                       participant_id=participant.id)


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
        return jsonify(status='success', url=participant.get_absolute_url())


class ParticipantBadge(PermissionRequiredMixin, MethodView):

    permission_required = ('view_participant', )

    def get(self, participant_id):
        participant = (
            Participant.query.current_meeting()
            .filter_by(id=participant_id)
            .first_or_404())
        nostripe = request.args.get('nostripe')
        context = {'participant': participant, 'nostripe': nostripe}
        return PdfRenderer('meetings/participant/badge.html',
                           width='3.4in', height='2.15in',
                           footer=False, orientation='portrait',
                           context=context).as_response()


class ParticipantLabel(PermissionRequiredMixin, MethodView):

    permission_required = ('view_participant', )

    def get(self, participant_id):
        participant = (
            Participant.query.current_meeting().participants()
            .filter_by(id=participant_id)
            .first_or_404())
        context = {'participant': participant}
        return PdfRenderer('meetings/participant/label.html',
                           height="8.3in", width="11.7in",
                           orientation="landscape", footer=False,
                           context=context).as_response()


class ParticipantEnvelope(PermissionRequiredMixin, MethodView):

    permission_required = ('view_participant', )

    def get(self, participant_id):
        participant = (
            Participant.query.current_meeting().participants()
            .filter_by(id=participant_id)
            .first_or_404())
        context = {'participant': participant}
        return PdfRenderer('meetings/participant/envelope.html',
                           height='6.4in', width='9.0in',
                           orientation="portrait", footer=False,
                           context=context).as_response()


class ParticipantAcknowledgeEmail(PermissionRequiredMixin, MethodView):

    template_name = 'meetings/participant/acknowledge.html'
    permission_required = ('view_participant', )

    def get_participant(self, participant_id):
        return (
            Participant.query.current_meeting().participants()
            .filter_by(id=participant_id)
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
            attachement = PdfRenderer('meetings/printouts/printout.html',
                                      height='11.7in',
                                      width='8.26in',
                                      orientation='portrait',
                                      as_attachement=True,
                                      context=context).as_attachement()
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
        participant = (
            Participant.query.current_meeting().participants()
            .filter_by(id=participant_id)
            .first_or_404())
        context = {'participant': participant}
        language = getattr(participant, 'lang', 'english')
        set_language(language)
        return PdfRenderer('meetings/printouts/acknowledge_detail.html',
                           height='11.7in', width='8.26in',
                           orientation='portrait', footer=False,
                           context=context).as_response()


class ParticipantsExport(PermissionRequiredMixin, MethodView):

    permission_required = ('view_participant', )

    def get(self):

        participants = get_participants_full(g.meeting.id)

        columns = []

        custom_fields = (
            g.meeting.custom_fields
            .filter_by(custom_field_type=CustomField.PARTICIPANT,
                       is_primary=True))
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
            data['category_id'] = p.category.title
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
