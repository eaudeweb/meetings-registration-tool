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

from mrt.forms.meetings import BadgeCategories, PrintoutForm
from mrt.models import Participant, Category, Meeting, Job
from mrt.models import redis_store, db
from mrt.pdf import render_pdf
from mrt.template import pluralize


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
        participants = Participant.query.filter_by(meeting=g.meeting)
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
        q = Queue(Job.PRINTOUTS_QUEUE,
                  connection=redis_store.connection,
                  default_timeout=1200)
        job_redis = q.enqueue(_process_badges, g.meeting.id, category_ids)
        job = Job(id=job_redis.id, name=self.JOB_NAME, user_id=current_user.id,
                  status=job_redis.get_status(), date=job_redis.enqueued_at,
                  meeting_id=g.meeting.id, queue=Job.PRINTOUTS_QUEUE)
        db.session.add(job)
        db.session.commit()
        url = url_for('.processing_file_list')
        flash('Started processing %s. You can see the progress in the '
              '<a href="%s">processing file list section</a>.' %
              (self.JOB_NAME, url), 'success')
        return redirect(url_for('.printouts_participant_badges'))


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


def _process_badges(meeting_id, category_ids):
        g.meeting = Meeting.query.get(meeting_id)
        participants = Participant.query.filter_by(meeting=g.meeting)
        if category_ids:
            participants = participants.filter(
                Participant.category.has(Category.id.in_(category_ids))
            )
        return render_pdf('meetings/printouts/badges_pdf.html',
                          participants=participants,
                          height='2.15in', width='3.4in',
                          orientation='portrait')


class ShortList(MethodView):

    def get(self):
        page = request.args.get('page', 1, type=int)
        category_ids = request.args.getlist('categories')
        printout_type = request.args.get('printout_type', 'verified', type=str)
        participants = (
            Participant.query.join(Participant.category)
            .filter_by(meeting=g.meeting).active()
            .order_by(Category.sort))

        if category_ids:
            participants = participants.filter(Category.id.in_(category_ids))
        if printout_type == 'attending':
            participants = participants.filter(Participant.attended == True)

        participant_count = participants.count()
        participants = participants.paginate(page, per_page=50)
        categories_form = PrintoutForm(request.args)
        return render_template('meetings/printouts/short_list.html',
                               printout_type=printout_type,
                               participants=participants,
                               participant_count=participant_count,
                               category_ids=category_ids,
                               categories_form=categories_form)
