
from flask import g, url_for, flash
from flask.ext.login import current_user
from mrt.models import Job
from mrt.models import redis_store, db
from rq import Queue


_PRINTOUT_MARGIN = {
    'top': '0.5in',
    'bottom': '0.5in',
    'left': '0.8in',
    'right': '0.8in',
}


def _add_to_printout_queue(method, job_name, *args):
    q = Queue(Job.PRINTOUTS_QUEUE, connection=redis_store._redis_client,
              default_timeout=1200)
    job_redis = q.enqueue(method, g.meeting.id, *args, result_ttl=86400)
    job = Job(id=job_redis.id,
              name=job_name,
              user_id=current_user.id,
              status=job_redis.get_status(),
              date=job_redis.enqueued_at,
              meeting_id=g.meeting.id,
              queue=Job.PRINTOUTS_QUEUE)
    db.session.add(job)
    db.session.commit()
    url = url_for('meetings.processing_file_list')
    flash('Started processing %s. You can see the progress in the '
          '<a href="%s">processing file list section</a>.' %
          (job_name, url), 'success')
