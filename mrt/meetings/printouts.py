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

from mrt.forms.meetings import BadgeCategories
from mrt.models import Participant, Category, Meeting, Job
from mrt.models import redis_store, db
from mrt.pdf import render_pdf


class ProcessingFileList(MethodView):

    decorators = (login_required,)

    def get(self):
        jobs = Job.query.order_by(desc(Job.date))
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
        q = Queue('badges', connection=redis_store.connection,
                  default_timeout=1200)
        job_redis = q.enqueue(_process_badges, g.meeting.id, category_ids)
        job = Job(id=job_redis.id, name=self.JOB_NAME,
                  user_id=current_user.id, status=job_redis.get_status(),
                  date=job_redis.enqueued_at)
        db.session.add(job)
        db.session.commit()
        flash('Started processing %s.' % self.JOB_NAME, 'success')
        return redirect(url_for('.printouts_participant_badges'))


class JobStatus(MethodView):

    decorators = (login_required,)

    def get(self):
        job_id = request.args['job_id']
        with Connection(redis_store.connection):
            try:
                job = JobRedis.fetch(job_id)
            except NoSuchJobError:
                abort(404)

            if job.is_finished:
                return jsonify(status=job.get_status(), result=job.result)
            else:
                return jsonify(status=job.get_status())


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
