import io
import mimetypes
import uuid

import openpyxl
import zipfile

import collections
from datetime import datetime
from itertools import groupby
from operator import attrgetter

import requests
from flask import flash
from path import Path
from werkzeug.datastructures import FileStorage
from werkzeug.datastructures import ImmutableMultiDict

from flask import current_app as app
from flask import g, url_for
from flask import request, render_template, jsonify, abort, redirect, Response
from flask import send_from_directory
from flask_login import login_required, current_user
from flask.views import MethodView

from rq import Connection
from rq.job import Job as JobRedis
from rq.job import NoSuchJobError
from sqlalchemy import desc
from sqlalchemy.orm import joinedload

from mrt.custom_country import Country, get_all_countries
from mrt.forms.meetings import BadgeCategories, EventsForm
from mrt.forms.meetings import FlagForm, CategoryTagForm
from mrt.forms.meetings import ParticipantEditForm
from mrt.forms.meetings import custom_form_factory
from mrt.forms.meetings import custom_object_factory
from mrt.models import Participant, Category, CategoryTag, Meeting, Job
from mrt.models import redis_store, db, CustomFieldValue, CustomField, CustomFieldChoice
from mrt.models import get_participants_full
from mrt.models import Action
from mrt.pdf import PdfRenderer
from mrt.template import pluralize, url_external
from mrt.meetings.mixins import PermissionRequiredMixin
from mrt.common.printouts import _add_to_printout_queue
from mrt.common.printouts import _PRINTOUT_MARGIN

from mrt.utils import parse_rfc6266_header
from mrt.utils import read_sheet, generate_excel, generate_import_excel
from openpyxl.utils.exceptions import InvalidFileException
from mrt.forms.meetings import ParticipantEditForm, MediaParticipantEditForm
from mrt.forms.meetings import custom_form_factory
from mrt.utils import str2bool

class ProcessingFileList(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', 'manage_participant',
                           'view_participant', 'manage_media_participant',
                           'view_media_participant')

    def get(self):
        page = request.args.get('page', 1, type=int)
        jobs = Job.query.filter_by(meeting=g.meeting).order_by(desc(Job.date))
        if not (current_user.has_perms(['manage_meeting'], g.meeting.id) or
                current_user.is_superuser):
            jobs = jobs.filter_by(user_id=current_user.id)
        jobs = jobs.paginate(page, per_page=50)
        return render_template('meetings/printouts/processing_file_list.html',
                               jobs=jobs)


class Badges(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', 'manage_participant',
                           'view_participant')

    JOB_NAME = 'participant categories'

    def get(self):
        category_ids = request.args.getlist('categories')
        page = request.args.get('page', 1, type=int)
        flag = request.args.get('flag')
        participants = Participant.query.current_meeting().participants()
        if category_ids:
            participants = participants.filter(
                Participant.category.has(Category.id.in_(category_ids))
            )
        if flag:
            attr = getattr(Participant, flag)
            participants = participants.filter(attr == True)
        badge_categories_form = BadgeCategories(request.args)
        participants = participants.paginate(page, per_page=50)
        return render_template('meetings/printouts/badges.html',
                               participants=participants,
                               category_ids=category_ids,
                               flag=flag,
                               badge_categories_form=badge_categories_form)

    def post(self):
        category_ids = request.args.getlist('categories')
        size = request.form.get('printout_size', 'default')
        flag = request.args.get('flag')
        _add_to_printout_queue(_process_badges, self.JOB_NAME,
                               flag, size, category_ids)
        return redirect(url_for('.printouts_participant_badges',
                                categories=category_ids, flag=flag))


def _process_badges(meeting_id, flag, size, category_ids):
    g.meeting = Meeting.query.get(meeting_id)
    participants = Participant.query.current_meeting().participants()
    if category_ids:
        participants = participants.filter(
            Participant.category.has(Category.id.in_(category_ids))
        )
    if flag:
        attr = getattr(Participant, flag)
        participants = participants.filter(attr == True)
    context = {'participants': participants, 'printout_size': size}
    w, h = ('8.3in', '11.7in') if size == 'A4' else ('3.4in', '2.15in')
    return PdfRenderer('meetings/printouts/badges_pdf.html',
                       width=w, height=h, orientation='portrait',
                       footer=False, context=context).as_rq()


class JobStatus(MethodView):

    decorators = (login_required,)

    def get(self):
        job_id = request.args['job_id']
        job = Job.query.get_or_404(job_id)

        with Connection(redis_store._redis_client):
            try:
                job_redis = JobRedis.fetch(job.id)
            except NoSuchJobError:
                job.status = Job.FAILED
                db.session.commit()
                # abort(404)
                return Response(status=404)

            if job_redis.is_finished:
                result = {'status': job_redis.get_status(),
                          'result': job_redis.result}
            else:
                result = {'status': job_redis.get_status()}

            job.status = job_redis.get_status()
            job.result = job_redis.result
            db.session.commit()
            return jsonify(**result)


class QueueStatus(MethodView):

    decorators = (login_required,)

    def get(self, queue):
        jobs = Job.query.filter_by(
            queue=queue, status=Job.QUEUED, meeting_id=g.meeting.id)
        count = jobs.count()
        title = '%d processing job%s' % (count, pluralize(count))
        return jsonify(count=count, title=title)


class PDFDownload(MethodView):

    decorators = (login_required,)

    def get(self, filename):
        return send_from_directory(app.config['UPLOADED_PRINTOUTS_DEST'],
                                   filename)


class ShortList(PermissionRequiredMixin, MethodView):

    JOB_NAME = 'short list'
    DOC_TITLE = 'List of participants'

    permission_required = ('manage_meeting', 'manage_participant',
                           'view_participant')

    @staticmethod
    def _get_query(flag):
        query = (
            Participant.query.current_meeting().participants()
            .join(Participant.category, Category.title)
            .options(joinedload(Participant.category)
                     .joinedload(Category.title))
            .order_by(Category.sort, Category.id,
                      Participant.last_name, Participant.id)
        )

        if flag:
            attr = getattr(Participant, flag)
            query = query.filter(attr == True)

        return query

    def get(self):
        flag = request.args.get('flag')
        page = request.args.get('page', 1, type=int)
        query = self._get_query(flag)
        count = query.count()
        pagination = query.paginate(page, per_page=50)
        participants = groupby(pagination.items, key=attrgetter('category'))
        flag_form = FlagForm(request.args)
        flag = g.meeting.custom_fields.filter_by(slug=flag).first()
        return render_template(
            'meetings/printouts/short_list.html',
            participants=participants,
            pagination=pagination,
            count=count,
            title=self.DOC_TITLE,
            flag=flag,
            flag_form=flag_form)

    def post(self):
        flag = request.args.get('flag')
        _add_to_printout_queue(_process_short_list, self.JOB_NAME,
                               self.DOC_TITLE, flag)
        return redirect(url_for('.printouts_short_list', flag=flag))


class ProvisionalList(PermissionRequiredMixin, MethodView):

    JOB_NAME = 'participant list'
    DOC_TITLE = 'Provisional list as entered by participant'
    TITLE_MAP = {
        'attended': 'Final list of participants',
        'verified': 'List of acknowledged participants',
        'credentials': 'List of participants with checked credentials',
    }
    GROUPABLE_FIELDS = [
        "country",
        "category_id",
        "represented_region",
        "represented_country",
        "represented_organization",
        "language",
    ]

    permission_required = ('manage_meeting', 'manage_participant',
                           'view_participant')

    @staticmethod
    def _get_query(flag, categories):
        query = (
            Participant.query.current_meeting().participants()
            .join(Participant.category, Category.title)
            .options(joinedload(Participant.category)
                     .joinedload(Category.title))
        )
        if categories:
            query = query.filter(Participant.category_id.in_(categories))

        if flag:
            attr = getattr(Participant, flag)
            query = query.filter(attr == True)
        query = query.order_by(
            Category.sort, Category.id,
            Participant.representing,
            Participant.last_name, Participant.id,
        )
        return query

    @staticmethod
    def _get_all_fields():
        """Get all displayable fields for this meeting."""
        participant_form = custom_form_factory(ParticipantEditForm)
        return list(participant_form().exclude([
            CustomField.CHECKBOX,
            CustomField.IMAGE,
            CustomField.EVENT
        ]))

    @staticmethod
    def _get_default_field_ids():
        """Get default field ids to display."""
        selected_field_ids = [
            "first_name",
            "last_name",
            "category_id",
            "represented_region",
            "represented_country",
            "email",
        ]
        if g.meeting.address_field_id:
            selected_field_ids.append(g.meeting.address_field.slug)
        if g.meeting.telephone_field_id:
            selected_field_ids.append(g.meeting.telephone_field.slug)
        return selected_field_ids

    @classmethod
    def _get_selected_field_ids(cls):
        """Get the selected fields according to the request arguments."""
        default_field_ids = cls._get_default_field_ids()
        if "flag" not in request.args:
            return default_field_ids
        selected_field_ids = []
        for field in cls._get_all_fields():
            if str2bool(request.args.get("field_" + field.id, "off")):
                selected_field_ids.append(field.id)
        try:
            group_by = request.args["group_by"]
            if group_by and group_by not in selected_field_ids:
                selected_field_ids.append(group_by)
        except KeyError:
            pass

        return selected_field_ids or default_field_ids

    def get(self):
        flag = request.args.get('flag')
        title = self.TITLE_MAP.get(flag, self.DOC_TITLE)
        try:
            categories = map(int, request.args.getlist("category_filter"))
        except (KeyError, ValueError, TypeError):
            categories = []

        query = self._get_query(flag, categories)

        participants = list(query.all())
        count = len(participants)

        flag_form = FlagForm(request.args)
        flag = g.meeting.custom_fields.filter_by(slug=flag).first()
        participant_form = custom_form_factory(ParticipantEditForm)
        all_fields = self._get_all_fields()

        selected_field_ids = self._get_selected_field_ids()
        selected_fields = list(participant_form().get_fields(field_ids=selected_field_ids))

        final_results = self.group_participants(participant_form, participants)

        return render_template(
            'meetings/printouts/provisional_list.html',
            all_fields=all_fields,
            selected_field_ids=selected_field_ids,
            selected_fields=selected_fields,
            grouped_participants=final_results,
            count=count,
            title=title,
            flag_form=flag_form,
            flag=flag)

    @staticmethod
    def group_participants(participant_form, participants):
        # Group the participants on two levels:
        #  - the category
        #  - the specified group field of each category.
        grouped_participants = collections.defaultdict(lambda: collections.defaultdict(list))
        for participant in participants:
            obj = participant_form(obj=custom_object_factory(participant))
            category = participant.category, obj.category_id.render_data() or "---"
            group_key = Category.GROUP_FIELD[participant.category.group.code]
            group_value = (
                getattr(obj, group_key).label.text,
                getattr(obj, group_key).render_data() or "---"
            )
            # Include the sort field to ensure the sorting order is respected.
            grouped_participants[category][group_value].append(
                (
                    getattr(obj, participant.category.sort_field.code).render_data() or "---",
                    obj
                )
            )
        # Apply sorting rules
        # 1. Sort by category sort int.
        final_results = collections.OrderedDict(sorted(
            grouped_participants.items(), key=lambda x: x[0][0].sort
        ))
        for key, value in final_results.items():
            # 2. Sort by the custom group field for this category
            final_results[key] = collections.OrderedDict(sorted(value.items()))
            for participant_list in final_results[key].values():
                # 3. Sort by the custom sort field or this category
                participant_list.sort()
        return final_results

    def post(self):
        flag = request.args.get('flag')
        title = self.TITLE_MAP.get(flag, self.DOC_TITLE)
        try:
            categories = map(int, request.args.getlist("category_filter"))
        except (KeyError, ValueError, TypeError):
            categories = []
        selected_field_ids = self._get_selected_field_ids()
        _add_to_printout_queue(_process_provisional_list, self.JOB_NAME,
                               title, flag, None, selected_field_ids, categories)
        return redirect(url_for('.printouts_provisional_list', flag=flag))


class DelegationsList(PermissionRequiredMixin, MethodView):

    JOB_NAME = 'delegation list'
    DOC_TITLE = 'List of delegations (to prepare the meeting room)'

    permission_required = ('manage_meeting', 'manage_participant',
                           'view_participant')

    @staticmethod
    def _get_query(flag):
        query = (
            Participant.query.current_meeting().participants()
            .join(Participant.category, Category.title)
            .options(joinedload(Participant.category)
                     .joinedload(Category.title))
            .order_by(Category.sort, Category.id,
                      Participant.last_name, Participant.id)
        )

        if flag:
            attr = getattr(Participant, flag)
            query = query.filter(attr == True)

        return query

    def get(self):
        flag = request.args.get('flag')
        query = self._get_query(flag)
        participants = groupby(query, key=attrgetter('category'))
        flag_form = FlagForm(request.args)
        flag = g.meeting.custom_fields.filter_by(slug=flag).first()
        return render_template(
            'meetings/printouts/delegation_list.html',
            participants=participants,
            title=self.DOC_TITLE,
            flag=flag,
            flag_form=flag_form)

    def post(self):
        flag = request.args.get('flag')
        _add_to_printout_queue(_process_delegation_list, self.JOB_NAME,
                               self.DOC_TITLE, flag)
        return redirect(url_for('.printouts_delegation_list', flag=flag))


class EventList(PermissionRequiredMixin, MethodView):

    JOB_NAME = 'event list'
    DOC_TITLE = 'List of announced participants in events'

    permission_required = ('manage_meeting', 'manage_participant',
                           'view_participant')

    @staticmethod
    def _get_query(event_ids):
        query = (
            CustomFieldValue.query.filter(
                CustomFieldValue.participant.has(meeting_id=g.meeting.id),
                CustomFieldValue.custom_field.has(field_type='event'),
                CustomFieldValue.value == 'true')
            .order_by(CustomFieldValue.custom_field_id))

        if event_ids:
            query = (
                query.filter(CustomFieldValue.custom_field.has(
                    CustomField.id.in_(event_ids))))

        return query

    def get(self):
        event_ids = request.args.getlist('events')
        page = request.args.get('page', 1, type=int)
        query = self._get_query(event_ids)
        count = query.count()

        pagination = query.paginate(page, per_page=50)
        participants = groupby(pagination.items,
                               key=attrgetter('custom_field'))
        event_form = EventsForm(request.args)
        return render_template(
            'meetings/printouts/event_list.html',
            participants=participants,
            count=count,
            title=self.DOC_TITLE,
            event_ids=event_ids,
            event_form=event_form,
            pagination=pagination)

    def post(self):
        event_ids = request.args.getlist('events')
        _add_to_printout_queue(_process_event_list, self.JOB_NAME,
                               self.DOC_TITLE, event_ids)
        return redirect(url_for('.printouts_participant_events',
                                events=event_ids))


class BaseDistribution(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', 'manage_participant',
                           'view_participant')

    @staticmethod
    def _get_query(flag):
        query = (
            Participant.query.current_meeting().participants()
            .join(Participant.category, Category.title)
            .options(joinedload(Participant.category)
                     .joinedload(Category.title))
            .order_by(Participant.language, Category.sort)
        )

        if flag:
            attr = getattr(Participant, flag)
            query = query.filter(attr == True)

        return query

    def get(self):
        flag = request.args.get('flag')
        query = self._get_query(flag)
        count = query.count()
        participants = groupby(query, key=attrgetter('language'))
        flag_form = FlagForm(request.args)
        flag = g.meeting.custom_fields.filter_by(slug=flag).first()

        return render_template(
            'meetings/printouts/distribution.html',
            printout_type=self.printout_type,
            participants=participants,
            count=count,
            title=self.DOC_TITLE,
            table_class=self.table_class,
            flag=flag,
            flag_form=flag_form)

    def post(self):
        flag = request.args.get('flag')
        _add_to_printout_queue(_process_distribution, self.JOB_NAME,
                               self.printout_type, self.DOC_TITLE, flag)
        return redirect(url_for(self.view_name, flag=flag))


class DocumentDistribution(BaseDistribution):

    JOB_NAME = 'document distribution'
    DOC_TITLE = 'Distribution of documents'

    template = 'meetings/printouts/distribution.html'
    view_name = '.printouts_document_distribution'
    printout_type = 'distribution'
    table_class = 'table-bordered table-condensed'


class PigeonHoles(BaseDistribution):

    JOB_NAME = 'pigeon holes'
    DOC_TITLE = 'Pigeon holes'

    template = 'meetings/printouts/distribution.html'
    view_name = '.printouts_pigeon_holes'
    printout_type = 'pigeon'
    table_class = 'pigeon-holes'


class Admission(PermissionRequiredMixin, MethodView):

    JOB_NAME = 'admission'

    permission_required = ('manage_meeting', 'manage_participant',
                           'view_participant')

    @staticmethod
    def _get_query(flag, category_tags):
        query = (
            Participant.query.current_meeting().participants()
            .join(Participant.category, Category.title)
            .options(joinedload(Participant.category)
                     .joinedload(Category.title))
            .order_by(Category.sort)
            .order_by(Category.id)
        )

        category_ids = []
        for tag in category_tags:
            category_ids += [category.id for category in
                             tag.categories.filter_by(meeting_id=g.meeting.id)]

        if category_ids:
            query = query.filter(Participant.category_id.in_(category_ids))

        if flag:
            attr = getattr(Participant, flag)
            query = query.filter(attr == True)

        return query

    def get(self):
        flag = request.args.get('flag')
        category_tags = request.args.getlist('category_tags')
        category_tags = (CategoryTag.query
                         .filter(CategoryTag.id.in_(category_tags))
                         .all())
        page = request.args.get('page', 1, type=int)
        query = self._get_query(flag, category_tags)
        count = query.count()
        pagination = query.paginate(page, per_page=1000)
        participants = pagination.items
        flag_form = FlagForm(request.args)
        category_tags_form = CategoryTagForm(request.args)
        if not category_tags:
            title = 'General admission'
        else:
            title = (', '.join([tag.label for tag in category_tags]) +
                     ' admission')
        flag = g.meeting.custom_fields.filter_by(slug=flag).first()

        return render_template(
            'meetings/printouts/admission.html',
            participants=participants,
            pagination=pagination,
            count=count,
            title=title,
            flag=flag,
            category_tags=category_tags,
            flag_form=flag_form,
            category_tags_form=category_tags_form)

    def post(self):
        flag = request.args.get('flag')
        category_tags = request.args.getlist('category_tags')
        args = (flag, category_tags,)
        _add_to_printout_queue(_process_admission, self.JOB_NAME, *args)
        return redirect(url_for('.printouts_admission', flag=flag,
                                category_tags=category_tags))


class PrintoutFooter(MethodView):

    def get(self):
        return render_template('meetings/printouts/footer.html',
                               now=datetime.now())


def _process_short_list(meeting_id, title, flag):
    g.meeting = Meeting.query.get(meeting_id)
    query = ShortList._get_query(flag)
    count = query.count()
    participants = groupby(query, key=attrgetter('category'))
    flag = g.meeting.custom_fields.filter_by(slug=flag).first()
    context = {'participants': participants,
               'count': count,
               'title': title,
               'flag': flag,
               'template': 'meetings/printouts/_short_list_table.html'}

    return PdfRenderer('meetings/printouts/printout.html',
                       title=title,
                       height='11.693in', width='8.268in',
                       margin=_PRINTOUT_MARGIN, orientation='landscape',
                       context=context).as_rq()


def _process_provisional_list(meeting_id, title, flag, template_name=None, selected_field_ids=None, categories=None):
    g.meeting = Meeting.query.get(meeting_id)
    query = ProvisionalList._get_query(flag, categories)
    count = query.count()
    participants = query
    flag = g.meeting.custom_fields.filter_by(slug=flag).first()
    template_name = (template_name or
                     'meetings/printouts/_provisional_list_pdf.html')
    participant_form = custom_form_factory(ParticipantEditForm)
    grouped_participants = ProvisionalList.group_participants(participant_form, participants)

    context = {'participants': participants,
               'grouped_participants': grouped_participants,
               'count': count,
               'title': title,
               'flag': flag,
               'selected_field_ids': selected_field_ids,
               'template': template_name}

    return PdfRenderer('meetings/printouts/printout.html',
                       title=title,
                       height='11.693in', width='8.268in',
                       margin=_PRINTOUT_MARGIN, orientation='portrait',
                       context=context).as_rq()


def _process_delegation_list(meeting_id, title, flag):
    g.meeting = Meeting.query.get(meeting_id)
    query = DelegationsList._get_query(flag)
    participants = groupby(query, key=attrgetter('category'))
    flag = g.meeting.custom_fields.filter_by(slug=flag).first()
    context = {'participants': participants,
               'title': title,
               'flag': flag,
               'template': 'meetings/printouts/_delegation_list_table.html'}

    return PdfRenderer('meetings/printouts/printout.html',
                       title=title,
                       height='11.693in', width='8.268in',
                       margin=_PRINTOUT_MARGIN, orientation='landscape',
                       context=context).as_rq()


def _process_event_list(meeting_id, title, event_ids):
    g.meeting = Meeting.query.get(meeting_id)
    query = EventList._get_query(event_ids)
    count = query.count()
    participants = groupby(query, key=attrgetter('custom_field'))
    context = {'participants': participants,
               'count': count,
               'title': title,
               'template': 'meetings/printouts/_event_list_table.html'}

    return PdfRenderer('meetings/printouts/printout.html',
                       title=title,
                       height='11.693in', width='8.268in',
                       margin=_PRINTOUT_MARGIN, orientation='landscape',
                       context=context).as_rq()


def _process_admission(meeting_id, flag, category_tags):
    g.meeting = Meeting.query.get(meeting_id)
    category_tags = (CategoryTag.query
                     .filter(CategoryTag.id.in_(category_tags))
                     .all())
    query = Admission._get_query(flag, category_tags)
    participants = query.all()
    flag = g.meeting.custom_fields.filter_by(slug=flag).first()
    if not category_tags:
        title = 'General admission'
    else:
        title = (', '.join([tag.label for tag in category_tags])
                 + ' admission')
    context = {'participants': participants,
               'title': title,
               'flag': flag,
               'category_tags': category_tags,
               'template': 'meetings/printouts/_admission_table.html'}

    return PdfRenderer('meetings/printouts/printout.html',
                       title=title,
                       height='11.693in', width='8.268in',
                       margin=_PRINTOUT_MARGIN, orientation='landscape',
                       context=context).as_rq()


def _process_distribution(meeting_id, printout_type, title, flag):
    if printout_type == 'distribution':
        view_class = DocumentDistribution
    else:
        view_class = PigeonHoles
    g.meeting = Meeting.query.get(meeting_id)
    query = view_class._get_query(flag)
    participants = groupby(query, key=attrgetter('language'))
    flag = g.meeting.custom_fields.filter_by(slug=flag).first()
    context = {'participants': participants,
               'title': title,
               'printout_type': view_class.printout_type,
               'table_class': view_class.table_class,
               'flag': flag,
               'template': 'meetings/printouts/_distribution_table.html'}

    return PdfRenderer('meetings/printouts/printout.html',
                       title=title,
                       height='11.693in', width='8.268in',
                       margin=_PRINTOUT_MARGIN, orientation='landscape',
                       context=context).as_rq()


class CategoriesForTags(MethodView):

    decorators = (login_required,)

    def get(self):
        category_tags = request.args.getlist('category_tags')
        categories = g.meeting.categories.order_by(Category.sort)
        if category_tags:
            categories = categories.filter(
                Category.tags.any(CategoryTag.id.in_(category_tags)))
        categories = [(c.id, c.title.english) for c in categories]
        return jsonify(categories)


class ParticipantsExport(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', 'view_participant',
                           'manage_participant')

    JOB_NAME = 'participants export excel'

    def post(self):
        _add_to_printout_queue(_process_export_participants_excel, self.JOB_NAME,
                               Participant.PARTICIPANT)
        return redirect(url_for('meetings.participants'))


class MediaParticipantsExport(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', 'view_media_participant',
                           'manage_media_participant')

    JOB_NAME = 'media participants export excel'

    def post(self):
        return redirect(url_for('meetings.media_participants'))


class DataImportTemplate(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', 'view_participant',
                           'manage_participant')

    def post(self):
        custom_fields = (
            g.meeting.custom_fields
            .filter_by(custom_field_type=self.participant_type)
            .order_by(CustomField.sort))
        custom_fields = [
            field for field in custom_fields
            if field.field_type.code != CustomField.EVENT
        ]

        meeting_categories = [c.title.english.lower() for c in
                              Category.get_categories_for_meeting(self.participant_type)]
        countries = [country[1].encode('utf-8') for country in get_all_countries()]

        file_name = 'import_{}_list_{}.xlsx'.format(self.participant_type, g.meeting.acronym)
        file_path = app.config['UPLOADED_PRINTOUTS_DEST'] / file_name
        generate_import_excel(custom_fields, file_path,
                              CustomField, meeting_categories,
                              countries)

        return send_from_directory(app.config['UPLOADED_PRINTOUTS_DEST'],
                                   file_name,
                                   as_attachment=True)


class ParticipantsImportTemplate(DataImportTemplate):

    JOB_NAME = 'participants import template'
    participant_type = Participant.PARTICIPANT


class MediaParticipantsImportTemplate(DataImportTemplate):

    JOB_NAME = 'media participants import template'
    participant_type = Participant.MEDIA


class DataImport(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', 'view_participant',
                           'manage_participant')

    def get(self):
        context = {
            "participant_type": self.participant_type,
        }
        return render_template('meetings/participant/import/list.html', **context)

    def post(self):
        if request.files.get("import_file"):
            try:
                xlsx = openpyxl.load_workbook(request.files["import_file"], read_only=True)
            except (zipfile.BadZipfile, InvalidFileException) as e:
                flash("Invalid XLS file: %s" % e, 'danger')
                context = {
                    "participant_type": self.participant_type,
                }
                return render_template('meetings/participant/import/list.html', **context)

            request.files["import_file"].seek(0)
            file_name = str(uuid.uuid4()) + '.xlsx'
            # Save the file so we only upload it once.
            request.files["import_file"].save(app.config['UPLOADED_PRINTOUTS_DEST'] / file_name)

        else:
            file_name = request.form["file_name"]
            try:
                xlsx = openpyxl.load_workbook(app.config['UPLOADED_PRINTOUTS_DEST'] / file_name, read_only=True)
            except (zipfile.BadZipfile, InvalidFileException) as e:
                flash("Invalid XLS file: %s" % e, 'danger')
                context = {
                    "participant_type": self.participant_type,
                }
                return render_template('meetings/participant/import/list.html', **context)

        custom_fields = (
            g.meeting.custom_fields
                .filter_by(custom_field_type=self.participant_type)
                .order_by(CustomField.sort))
        custom_fields = [field for field in custom_fields if field.field_type.code != CustomField.EVENT]

        has_errors = False

        try:
            rows = list(read_sheet(xlsx, custom_fields))
            assert rows, "file has no data"
        except (AssertionError, ValueError) as e:
            flash("Invalid XLS file: %s" % e, 'danger')
            context = {
                "participant_type": self.participant_type,
            }
            return render_template('meetings/participant/import/list.html', **context)

        forms = []
        for form in read_participants_excel(custom_fields, rows, self.form_class):
            has_errors = not form.validate() or has_errors
            forms.append(form)

        all_fields = list(custom_form_factory(self.form_class)().exclude([
            CustomField.EVENT,
        ]))
        context = {
            "forms": forms,
            "has_errors": has_errors,
            "all_fields": all_fields,
            "file_name": file_name,
            "participant_type": self.participant_type,
        }

        if has_errors:
            flash(
                'XLS file has errors, please review and correct them and try again. '
                'Hover over cells to find more about the errors.',
                'danger'
            )
        elif request.form["action"] == "import":
            _add_to_printout_queue(_process_import_participants_excel, self.JOB_NAME,
                                   rows, self.participant_type, self.form_class)
            context["import_started"] = True
        else:
            flash(
                'XLS file is valid, please review and hit "Start import" after.',
                'success',
            )

        return render_template('meetings/participant/import/list.html', **context)


class ParticipantsImport(DataImport):

    JOB_NAME = 'participants import'
    participant_type = Participant.PARTICIPANT
    form_class = ParticipantEditForm


class MediaParticipantsImport(DataImport):

    JOB_NAME = 'media participants import'
    participant_type = Participant.MEDIA
    form_class = MediaParticipantEditForm



def _process_export_participants_excel(meeting_id, participant_type):
    g.meeting = Meeting.query.get(meeting_id)
    participants = get_participants_full(g.meeting.id, participant_type)

    custom_fields = (
        g.meeting.custom_fields
        .filter_by(custom_field_type=participant_type)
        .order_by(CustomField.sort))

    columns = [cf.slug for cf in custom_fields]
    columns.append('registration_date')
    header = [cf.label.english for cf in custom_fields]
    header.append('Date of Registration')

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
        data['registration_date'] = (
            p.registration_date.strftime('%Y-%m-%d')
            if p.registration_date else None)

        for custom_field in added_custom_fields:

            if custom_field.field_type == CustomField.MULTI_CHECKBOX:
                custom_value = custom_field.custom_field_values.filter_by(
                    participant=p).all()
            else:
                custom_value = custom_field.custom_field_values.filter_by(
                    participant=p).first()

            if not custom_value:
                continue

            if custom_field.field_type == CustomField.COUNTRY:
                custom_value = Country(custom_value.value).name
            elif custom_field.field_type == CustomField.MULTI_CHECKBOX:
                custom_value = ', '.join([unicode(v.choice)
                                          for v in custom_value])
            else:
                custom_value = custom_value.value

            if custom_field.field_type in (CustomField.IMAGE,
                                           CustomField.DOCUMENT):
                file_path = Path(app.config['PATH_CUSTOM_KEY']) / custom_value
                file_url = url_external('files', filename=file_path)
                custom_value = file_url

            data[custom_field.slug] = custom_value

        rows.append([data.get(k) or '' for k in columns])

    filename = '{}_list_{}.xls'.format(participant_type, g.meeting.acronym)
    file_path = app.config['UPLOADED_PRINTOUTS_DEST'] / filename
    generate_excel(header, rows, str(file_path))
    return url_for('meetings.printouts_download', filename=filename)


def _process_import_participants_excel(meeting_id, participants_rows, participants_type, form_class):
    g.meeting = Meeting.query.get(meeting_id)

    custom_fields = (
        g.meeting.custom_fields
        .filter_by(custom_field_type=participants_type)
        .order_by(CustomField.sort))
    custom_fields = [
        field for field in custom_fields
        if field.field_type.code != CustomField.EVENT
    ]
    for form in read_participants_excel(custom_fields, participants_rows, form_class, read_files=True):
        # Paranoid validation
        if form.validate():
            form.save()
        else:
            raise AssertionError("".join(form.errors))

    return 'Successfully added'


def read_participants_excel(custom_fields, rows, form_class, read_files=False):
    meeting_categories = {}
    for c in Category.get_categories_for_meeting(form_class.CUSTOM_FIELDS_TYPE):
        meeting_categories[c.title.english.lower()] = c.id

    countries = {}
    for code, name in get_all_countries():
        countries[name.lower()] = code

    custom_fields = {
        custom_field.slug: custom_field for custom_field in custom_fields
    }

    Form = custom_form_factory(form_class)

    for row_num, row in enumerate(rows, start=2):
        participant_details = []
        for slug, value in row.items():
            value = value.strip()

            if not value:
                continue
            custom_field = custom_fields[slug]
            field_type = custom_field.field_type.code

            if field_type == CustomField.CATEGORY:
                value = meeting_categories.get(unicode(value).lower(), -1)
            elif field_type == CustomField.COUNTRY:
                value = countries.get(value.lower(), "invalid-country")
            elif field_type == CustomField.MULTI_CHECKBOX:
                value = [el.strip() for el in value.split(",")]
            elif field_type in (CustomField.IMAGE, CustomField.DOCUMENT):
                if read_files:
                    resp = requests.get(value, stream=True)
                    resp.raise_for_status()

                    content_type = resp.headers.get('content-type', 'application/octet-stream')
                    content_length = resp.headers.get('content-length', None)
                    filename = parse_rfc6266_header(resp.headers.get("content-disposition", "")).get("filename")

                    if not filename:
                        # Attempt to guess the extension of the file
                        ext = mimetypes.guess_extension(content_type)
                        if ext:
                            filename = str(uuid.uuid4()) + ext

                    value = FileStorage(
                        stream=io.BytesIO(resp.content),
                        filename=filename,
                        content_type=content_type,
                        content_length=content_length,
                        headers=resp.headers,
                    )
                else:
                    # TODO: Add some form of validation to check the URLs are valid
                    #  A HEAD request could also be done in theory fast enough.
                    pass

            if isinstance(value, list):
                # Multi checkbox values
                for val in value:
                    participant_details.append((slug, val))
            else:
                participant_details.append((slug, value))

        form = Form(formdata=ImmutableMultiDict(participant_details), read_from_request=False)
        form.excel_row = row_num
        # Set the original value so the frontend can present it as such.
        for slug, value in row.items():
            form[slug].excel_value = value.strip()
        yield form

