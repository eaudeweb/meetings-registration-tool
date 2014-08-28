from flask import g
from flask import request, render_template, Response
from flask.views import MethodView

from rq import Queue

from mrt.models import Participant, Category, Meeting
from mrt.models import redis_store
from mrt.pdf import render_pdf


class Printouts(MethodView):

    def get(self):
        categories = Category.query.filter_by(meeting=g.meeting)
        return render_template('meetings/printouts/list.html',
                               categories=categories)


class Badges(MethodView):

    def get(self):
        category_ids = request.args.getlist('categories')
        page = request.args.get('page', 1, type=int)
        participants = Participant.query.filter_by(meeting=g.meeting)
        if category_ids:
            participants = participants.filter(
                Participant.category.has(Category.id.in_(category_ids))
            )
        participants = participants.paginate(page, per_page=50)
        return render_template('meetings/printouts/badges.html',
                               participants=participants,
                               category_ids=category_ids)

    def head(self):
        category_ids = request.args.getlist('categories')
        q = Queue('badges', connection=redis_store.connection,
                  default_timeout=1200)
        job = q.enqueue(_process_badges, g.meeting.id, category_ids)
        return Response(headers={'X-Job-ID': job.id})


class Job(MethodView):

    def get(self, job_id):
        pass


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
