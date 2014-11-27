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

from mrt.forms.meetings import BadgeCategories
from mrt.models import Participant, Category, Meeting, Job
from mrt.models import redis_store, db
from mrt.pdf import PdfRenderer
from mrt.template import pluralize


_PRINTOUT_MARGIN = {'top': '0.5in', 'bottom': '0.5in', 'left': '0.8in',
                    'right': '0.8in'}


def _add_to_printout_queue(method, job_name, *args):
    q = Queue(Job.PRINTOUTS_QUEUE, connection=redis_store.connection,
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


class ProcessingFileList(MethodView):

    decorators = (login_required,)

    def get(self):
        page = request.args.get('page', 1, type=int)
        jobs = Job.query.filter_by(meeting=g.meeting).order_by(desc(Job.date))
        jobs = jobs.paginate(page, per_page=50)
        return render_template('meetings/printouts/processing_file_list.html',
                               jobs=jobs)


class Badges(MethodView):

    decorators = (login_required,)

    JOB_NAME = 'participant categories'

    def get(self):
        category_ids = request.args.getlist('categories')
        page = request.args.get('page', 1, type=int)
        participants = Participant.query.current_meeting().participants()
        if category_ids:
            participants = participants.filter(
                Participant.category.has(Category.id.in_(category_ids))
            )
        badge_categories_form = BadgeCategories(request.args)
        participants = participants.paginate(page, per_page=50)
        return render_template('meetings/printouts/badges.html',
                               participants=participants,
                               category_ids=category_ids,
                               badge_categories_form=badge_categories_form)

    def post(self):
        category_ids = request.args.getlist('categories')
        _add_to_printout_queue(_process_badges, self.JOB_NAME,
                               *[category_ids])
        return redirect(url_for('.printouts_participant_badges'))


def _process_badges(meeting_id, category_ids):
    g.meeting = Meeting.query.get(meeting_id)
    participants = Participant.query.current_meeting().participants()
    if category_ids:
        participants = participants.filter(
            Participant.category.has(Category.id.in_(category_ids))
        )
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

        with Connection(redis_store.connection):
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


class ShortList(MethodView):

    JOB_NAME = 'short list'
    DOC_TITLE = 'List of announced participants'

    decorators = (login_required,)

    @staticmethod
    def _get_query():
        return (
            Participant.query.current_meeting().participants()
            .join(Participant.category, Category.title)
            .options(joinedload(Participant.category)
                     .joinedload(Category.title))
            .order_by(Category.sort, Participant.last_name, Participant.id)
        )

    def get(self):
        page = request.args.get('page', 1, type=int)
        query = self._get_query()
        count = query.count()
        pagination = query.paginate(page, per_page=50)
        participants = groupby(pagination.items, key=attrgetter('category'))
        return render_template(
            'meetings/printouts/short_list.html',
            participants=participants,
            pagination=pagination,
            count=count,
            title=self.DOC_TITLE)

    def post(self):
        _add_to_printout_queue(_process_short_list, self.JOB_NAME,
                               self.DOC_TITLE)
        return redirect(url_for('.printouts_short_list'))


class DelegationsList(MethodView):

    JOB_NAME = 'delegation list'
    DOC_TITLE = 'List of delegations (to prepare the meeting room)'

    decorators = (login_required,)

    @staticmethod
    def _get_query():
        return (
            Participant.query.current_meeting().participants()
            .join(Participant.category, Category.title)
            .options(joinedload(Participant.category)
                     .joinedload(Category.title))
            .order_by(Category.sort, Participant.last_name, Participant.id)
        )

    def get(self):
        query = self._get_query()
        participants = groupby(query, key=attrgetter('category'))
        return render_template(
            'meetings/printouts/delegation_list.html',
            participants=participants,
            title=self.DOC_TITLE,)

    def post(self):
        _add_to_printout_queue(_process_delegation_list, self.JOB_NAME,
                               self.DOC_TITLE)
        return redirect(url_for('.printouts_short_list'))


class PrintoutFooter(MethodView):

    def get(self):
        return render_template('meetings/printouts/footer.html',
                               now=datetime.now())


def _process_short_list(meeting_id, title):
    g.meeting = Meeting.query.get(meeting_id)
    query = ShortList._get_query()
    count = query.count()
    participants = groupby(query, key=attrgetter('category'))
    context = {'participants': participants,
               'count': count,
               'title': title,
               'template': 'meetings/printouts/_short_list_table.html'}
    return PdfRenderer('meetings/printouts/printout.html',
                       title=title,
                       height='11.693in', width='8.268in',
                       margin=_PRINTOUT_MARGIN, orientation='landscape',
                       context=context).as_rq()


def _process_delegation_list(meeting_id, title):
    g.meeting = Meeting.query.get(meeting_id)
    query = DelegationsList._get_query()
    participants = groupby(query, key=attrgetter('category'))
    context = {'participants': participants,
               'title': title,
               'template': 'meetings/printouts/_delegation_list_table.html'}

    return PdfRenderer('meetings/printouts/printout.html',
                       title=title,
                       height='11.693in', width='8.268in',
                       margin=_PRINTOUT_MARGIN, orientation='landscape',
                       context=context).as_rq()
