from datetime import datetime
from itertools import groupby
from operator import attrgetter

from flask import current_app as app
from flask import g, flash, url_for
from flask import request, render_template, jsonify, abort, redirect
from flask import send_from_directory
from flask.ext.login import login_required, current_user
from flask.views import MethodView

from rq import Queue, Connection
from rq.job import Job as JobRedis
from rq.job import NoSuchJobError
from sqlalchemy import desc
from sqlalchemy.orm import joinedload

from mrt.forms.meetings import BadgeCategories, EventsForm
from mrt.forms.meetings import FlagForm, CategoryTagForm
from mrt.models import Participant, Category, CategoryTag, Meeting, Job
from mrt.models import redis_store, db, CustomFieldValue, CustomField
from mrt.pdf import PdfRenderer
from mrt.template import pluralize
from mrt.meetings.mixins import PermissionRequiredMixin


_PRINTOUT_MARGIN = {'top': '0.5in', 'bottom': '0.5in', 'left': '0.8in',
                    'right': '0.8in'}


def _add_to_printout_queue(method, job_name, *args):
    q = Queue(Job.PRINTOUTS_QUEUE, connection=redis_store._redis_client,
              default_timeout=1200)
    job_redis = q.enqueue(method, g.meeting.id, *args)
    job = Job(id=job_redis.id,
              name=job_name,
              user_id=current_user.id,
              status=job_redis.get_status(),
              date=job_redis.enqueued_at,
              meeting_id=g.meeting.id,
              queue=Job.PRINTOUTS_QUEUE)
    db.session.add(job)
    db.session.commit()
    url = url_for('.processing_file_list')
    flash('Started processing %s. You can see the progress in the '
          '<a href="%s">processing file list section</a>.' %
          (job_name, url), 'success')


class ProcessingFileList(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', 'manage_participant',
                           'view_participant')

    def get(self):
        page = request.args.get('page', 1, type=int)
        jobs = Job.query.filter_by(meeting=g.meeting).order_by(desc(Job.date))
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
        flag = request.args.get('flag')
        _add_to_printout_queue(_process_badges, self.JOB_NAME,
                               flag, *[category_ids])
        return redirect(url_for('.printouts_participant_badges',
                                categories=category_ids, flag=flag))


def _process_badges(meeting_id, flag, category_ids):
    g.meeting = Meeting.query.get(meeting_id)
    participants = Participant.query.current_meeting().participants()
    if category_ids:
        participants = participants.filter(
            Participant.category.has(Category.id.in_(category_ids))
        )
    if flag:
            attr = getattr(Participant, flag)
            participants = participants.filter(attr == True)
    context = {'participants': participants}
    return PdfRenderer('meetings/printouts/badges_pdf.html',
                       height='2.15in', width='3.4in',
                       orientation='portrait',
                       context=context).as_rq()


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
                abort(404)

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
        jobs = Job.query.filter_by(queue=queue, status=Job.QUEUED)
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
                      Participant.represented_country.name,
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
        participants = pagination.items
        flag_form = FlagForm(request.args)
        flag = g.meeting.custom_fields.filter_by(slug=flag).first()
        return render_template(
            'meetings/printouts/provisional_list.html',
            participants=participants,
            pagination=pagination,
            count=count,
            title=self.DOC_TITLE,
            flag_form=flag_form,
            flag=flag)

    def post(self):
        flag = request.args.get('flag')
        _add_to_printout_queue(_process_provisional_list, self.JOB_NAME,
                               self.DOC_TITLE, flag)
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


class DocumentDistribution(PermissionRequiredMixin, MethodView):

    JOB_NAME = 'document distribution'
    DOC_TITLE = 'Distribution of documents'

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
        page = request.args.get('page', 1, type=int)
        query = self._get_query(flag)
        count = query.count()
        pagination = query.paginate(page, per_page=1000)
        participants = groupby(pagination.items, key=attrgetter('language'))
        flag_form = FlagForm(request.args)
        flag = g.meeting.custom_fields.filter_by(slug=flag).first()

        categories_map = {}
        for category in g.meeting.categories:
            categories_map[category.sort] = category

        return render_template(
            'meetings/printouts/document_distribution.html',
            categories_map=categories_map,
            participants=participants,
            pagination=pagination,
            count=count,
            title=self.DOC_TITLE,
            flag=flag,
            flag_form=flag_form)

    def post(self):
        flag = request.args.get('flag')
        _add_to_printout_queue(_process_document_distribution, self.JOB_NAME,
                               self.DOC_TITLE, flag)
        return redirect(url_for('.printouts_document_distribution'))


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


def _process_provisional_list(meeting_id, title, flag):
    g.meeting = Meeting.query.get(meeting_id)
    query = ProvisionalList._get_query(flag)
    count = query.count()
    participants = query
    flag = g.meeting.custom_fields.filter_by(slug=flag).first()
    context = {'participants': participants,
               'count': count,
               'title': title,
               'flag': flag,
               'template': 'meetings/printouts/_provisional_list_pdf.html'}
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

def _process_document_distribution(meeting_id, title, flag):
    g.meeting = Meeting.query.get(meeting_id)
    query = DocumentDistribution._get_query(flag)
    participants = groupby(query, key=attrgetter('language'))
    flag = g.meeting.custom_fields.filter_by(slug=flag).first()
    context = {'participants': participants,
               'title': title,
               'flag': flag,
               'template': 'meetings/printouts/_document_distribution_table.html'}

    return PdfRenderer('meetings/printouts/printout.html',
                       title=title,
                       height='11.693in', width='8.268in',
                       margin=_PRINTOUT_MARGIN, orientation='landscape',
                       context=context).as_rq()
