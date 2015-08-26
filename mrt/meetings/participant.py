from functools import wraps

from sqlalchemy_utils.types.country import Country

from werkzeug.utils import HTMLBuilder

from flask import g, request, redirect, url_for, jsonify, json
from flask import render_template, flash, Response
from flask.ext.login import current_user as user
from flask.views import MethodView

from mrt.forms.meetings import AcknowledgeEmailForm
from mrt.forms.meetings import custom_form_factory, custom_object_factory
from mrt.forms.meetings import MediaParticipantEditForm
from mrt.forms.meetings import ParticipantDummyForm, ParticipantEditForm

from mrt.admin.mixins import PermissionRequiredMixin as AdminPermRequiredMixin
from mrt.meetings.mixins import PermissionRequiredMixin
from mrt.mixins import FilterView

from mrt.mail import send_single_message
from mrt.models import db, Participant, CustomField, Category, Phrase
from mrt.models import search_for_participant, get_participants_full

from mrt.definitions import BADGE_W, BADGE_H, LABEL_W, LABEL_H, ENVEL_W
from mrt.definitions import ENVEL_H, ACK_W, ACK_H
from mrt.pdf import PdfRenderer
from mrt.signals import activity_signal
from mrt.utils import generate_excel, set_language
from mrt.utils import JSONEncoder


def _check_category(category_type):
    query = (Category.query.filter_by(meeting=g.meeting)
             .filter_by(category_type=category_type))
    if query.count() == 0:
        return render_template('meetings/category_required.html')


def _participant_category_required(func):
    @wraps(func)
    def wrapper(**kwargs):
        return _check_category(Category.PARTICIPANT) or func(**kwargs)
    return wrapper


def _media_participant_category_required(func):
    @wraps(func)
    def wrapper(**kwargs):
        return _check_category(Category.MEDIA) or func(**kwargs)
    return wrapper


class Participants(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', 'view_participant',
                           'manage_participant')
    form_class = ParticipantEditForm

    def get(self):
        Form = custom_form_factory(self.form_class)
        form = Form()
        return render_template('meetings/participant/participant/list.html',
                               form=form)


class MediaParticipants(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', 'view_media_participant',
                           'manage_media_participant')

    def get(self):
        return render_template('meetings/participant/media/list.html')


class ParticipantsFilter(PermissionRequiredMixin, MethodView, FilterView):

    permission_required = ('manage_meeting', 'view_participant',
                           'manage_participant')

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

    permission_required = ('manage_meeting', 'view_media_participant',
                           'manage_media_participant')

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

    permission_required = ('manage_meeting', 'view_participant',
                           'manage_participant')

    def get(self):
        participants = search_for_participant(request.args['search'])
        results = []
        for p in participants:
            results.append({
                'value': p.name,
                'url': url_for('.participant_detail', participant_id=p.id)
            })
        return json.dumps(results)


class BaseParticipantSearch(PermissionRequiredMixin, MethodView):

    def get_queryset(self):
        raise NotImplemented

    def serialize_participant(self, form):
        raise NotImplemented

    def get(self):
        queryset = self.get_queryset()
        participants = search_for_participant(request.args['search'], queryset)
        results = []
        Form = custom_form_factory(self.form_class)
        for p in participants:
            Object = custom_object_factory(p)
            form = Form(obj=Object())
            info = self.serialize_participant(form)
            info['value'] = p.name
            results.append(info)
        return json.dumps(results, cls=JSONEncoder)


class DefaultParticipantSearch(BaseParticipantSearch):

    permission_required = ('manage_meeting', 'manage_participant')
    form_class = ParticipantEditForm

    def get_queryset(self):
        return Participant.query.default_participants()

    def serialize_participant(self, form):
        info = {x: y.data for x, y in form._fields.iteritems()}
        info['represented_country'] = (
            info['represented_country'] and
            info['represented_country'].code)
        info['country'] = info['country'] and info['country'].code
        return info


class DefaultMediaParticipantSearch(BaseParticipantSearch):

    permission_required = ('manage_meeting', 'manage_media_participant')
    form_class = MediaParticipantEditForm

    def get_queryset(self):
        return Participant.query.default_media_participants()

    def serialize_participant(self, form):
        info = {x: y.data for x, y in form._fields.iteritems()}
        return info


class BaseParticipantDetail(MethodView):

    def _get_queryset(self):
        raise NotImplemented

    def get(self, participant_id):
        participant = self._get_queryset(participant_id)
        Form = custom_form_factory(self.form_class)
        Object = custom_object_factory(participant)
        form = Form(obj=Object())
        return render_template(self.template, participant=participant,
                               form=form)


class ParticipantDetail(PermissionRequiredMixin, BaseParticipantDetail):

    permission_required = ('manage_meeting', 'view_participant',
                           'manage_participant')
    form_class = ParticipantEditForm
    template = 'meetings/participant/participant/detail.html'

    def _get_queryset(self, participant_id):
        return (Participant.query.current_meeting().participants()
                .filter_by(id=participant_id)
                .first_or_404())


class MediaParticipantDetail(PermissionRequiredMixin, BaseParticipantDetail):

    permission_required = ('manage_meeting', 'view_media_participant',
                           'manage_media_participant')
    form_class = MediaParticipantEditForm
    template = 'meetings/participant/media/detail.html'

    def _get_queryset(self, participant_id):
        return (Participant.query.current_meeting().media_participants()
                .filter_by(id=participant_id)
                .first_or_404())


class DefaultParticipantDetail(AdminPermRequiredMixin, BaseParticipantDetail):

    form_class = ParticipantEditForm
    template = 'meetings/participant/default/participant_detail.html'

    def _get_queryset(self, participant_id):
        return (Participant.query.current_meeting().default_participants()
                .filter_by(id=participant_id)
                .first_or_404())


class DefaultMediaParticipantDetail(AdminPermRequiredMixin,
                                    BaseParticipantDetail):

    form_class = MediaParticipantEditForm
    template = 'meetings/participant/default/media_detail.html'

    def _get_queryset(self, participant_id):
        return (Participant.query.current_meeting()
                .default_media_participants()
                .filter_by(id=participant_id)
                .first_or_404())


class BaseParticipantEdit(MethodView):

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


class ParticipantEdit(PermissionRequiredMixin, BaseParticipantEdit):

    permission_required = ('manage_meeting', 'manage_participant')
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

    permission_required = ('manage_meeting', 'manage_media_participant')
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


class DefaultParticipantEdit(AdminPermRequiredMixin, BaseParticipantEdit):

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

    permission_required = ('manage_meeting', 'manage_participant')

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


class ParticipantPermanentlyDelete(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', 'manage_participant')

    def delete(self, participant_id):
        participant = (
            Participant.query
            .filter_by(meeting_id=g.meeting.id, id=participant_id)
            .first_or_404())
        db.session.delete(participant)
        db.session.commit()
        flash('Participant permanently delete', 'success')
        return jsonify(status='success', url=url_for('.activity'))


class ParticipantBadge(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting',
                           'view_participant', 'manage_participant',
                           'view_media_participant', 'manage_media_participant'
                           )

    def get(self, participant_id):
        participant = (
            Participant.query.current_meeting()
            .filter_by(id=participant_id)
            .first_or_404())
        nostripe = request.args.get('nostripe')
        context = {'participant': participant, 'nostripe': nostripe}
        return PdfRenderer('meetings/participant/badge.html',
                           width=BADGE_W, height=BADGE_H,
                           footer=False, orientation='portrait',
                           context=context).as_response()


class ParticipantLabel(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', 'view_participant',
                           'manage_participant')

    def get(self, participant_id):
        participant = (
            Participant.query.current_meeting().participants()
            .filter_by(id=participant_id)
            .first_or_404())
        context = {'participant': participant}
        return PdfRenderer('meetings/participant/label.html',
                           width=LABEL_W, height=LABEL_H,
                           orientation="landscape", footer=False,
                           context=context).as_response()


class ParticipantEnvelope(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', 'view_participant',
                           'manage_participant')

    def get(self, participant_id):
        participant = (
            Participant.query.current_meeting().participants()
            .filter_by(id=participant_id)
            .first_or_404())

        set_language(participant.lang)

        context = {'participant': participant}

        return PdfRenderer('meetings/participant/envelope.html',
                           width=ENVEL_W, height=ENVEL_H,
                           orientation="portrait", footer=False,
                           context=context).as_response()


class ParticipantAcknowledgeEmail(PermissionRequiredMixin, MethodView):

    template_name = 'meetings/participant/acknowledge.html'
    permission_required = ('manage_meeting', 'manage_participant')

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
            attachment = PdfRenderer('meetings/printouts/printout.html',
                                     width=ACK_W,
                                     height=ACK_H,
                                     orientation='portrait',
                                     as_attachment=True,
                                     context=context).as_attachment()
            if send_single_message(form.to.data, form.subject.data,
                                   form.message.data,
                                   attachment=attachment,
                                   attachment_name='registration_detail.pdf'):
                flash('Message successfully sent', 'success')
                return redirect(url_for('.participant_detail',
                                        participant_id=participant.id))
            else:
                flash('Message failed to send', 'error')

        set_language(participant.lang)
        return render_template(self.template_name, participant=participant,
                               form=form)


class ParticipantAcknowledgePDF(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', 'view_participant',
                           'manage_participant')

    def get(self, participant_id):
        participant = (
            Participant.query.current_meeting().participants()
            .filter_by(id=participant_id)
            .first_or_404())
        context = {'participant': participant}
        language = getattr(participant, 'lang', 'english')
        set_language(language)
        return PdfRenderer('meetings/printouts/acknowledge_detail.html',
                           width=ACK_W, height=ACK_H,
                           orientation='portrait', footer=False,
                           context=context).as_response()


class ParticipantsExport(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', 'view_participant',
                           'manage_participant')

    def get(self):
        participants = get_participants_full(g.meeting.id)

        custom_fields = (
            g.meeting.custom_fields
            .filter_by(custom_field_type=CustomField.PARTICIPANT)
            .filter(CustomField.field_type.notin_((unicode(CustomField.IMAGE),
                                                   unicode(CustomField.DOCUMENT))))
            .order_by(CustomField.sort))

        columns = [cf.slug for cf in custom_fields]
        header = [cf.label.english for cf in custom_fields]

        added_custom_fields = custom_fields.filter_by(is_primary=False)

        rows = []

        for p in participants:
            data = {}
            data['title'] = p.title.value
            data['first_name'] = p.first_name
            data['last_name'] = p.last_name
            data['badge_name'] = p.name_on_badge
            data['country'] = p.country.name if p.country else None
            data['email'] = p.email
            data['language'] = getattr(p.language, 'value', '-')
            data['category_id'] = p.category.title
            data['represented_country'] = (
                p.represented_country.name if p.represented_country else None)
            data['represented_region'] = (
                p.represented_region.value if p.represented_region else None)
            data['represented_organization'] = p.represented_organization
            data['attended'] = 'Yes' if p.attended else None
            data['verified'] = 'Yes' if p.verified else None
            data['credentials'] = 'Yes' if p.credentials else None

            for custom_field in added_custom_fields:
                if custom_field .field_type == CustomField.MULTI_CHECKBOX:
                    custom_value = custom_field.custom_field_values.filter_by(participant=p).all()
                else:
                    custom_value = custom_field.custom_field_values.filter_by(participant=p).first()

                if not custom_value:
                    continue

                if custom_field.field_type == CustomField.COUNTRY:
                    custom_value = Country(custom_value.value).name
                elif custom_field.field_type == CustomField.MULTI_CHECKBOX:
                    custom_value = ', '.join([unicode(v.choice) for v in custom_value])
                else:
                    custom_value = custom_value.value

                data[custom_field.slug] = custom_value

            rows.append([data.get(k) or '' for k in columns])

        return Response(
            generate_excel(header, rows),
            mimetype='application/vnd.ms-excel',
            headers={'Content-Disposition': 'attachment; filename=%s.xls'
                     % 'registration'})
