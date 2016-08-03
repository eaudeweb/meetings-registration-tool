from flask import url_for
from pyquery import PyQuery
from rq import Queue
from mrt.models import redis_store, Job, db
from mrt.meetings.printouts import _process_short_list
from .factories import RoleUserMeetingFactory
from .factories import RoleFactory, JobsFactory


def test_meeting_manager(app):
    first_role = RoleFactory(permissions=('manage_meeting',))
    second_role = RoleFactory(permissions=('view_participant',))
    first_role_user = RoleUserMeetingFactory(role=first_role)
    second_role_user = RoleUserMeetingFactory(role=second_role,
                                              meeting=first_role_user.meeting)

    q = Queue(Job.PRINTOUTS_QUEUE, connection=redis_store._redis_client,
              default_timeout=1200)
    first_job_redis = q.enqueue(_process_short_list,
                                first_role_user.meeting.id,
                                'List of participants', 'verified')
    second_job_redis = q.enqueue(_process_short_list,
                                 first_role_user.meeting.id,
                                 'List of participants', 'verified')
    first_job = JobsFactory(id=first_job_redis.id,
                            user_id=first_role_user.user.id,
                            meeting_id=first_role_user.meeting.id)
    second_job = JobsFactory(id=second_job_redis.id,
                             user_id=second_role_user.user.id,
                             meeting_id=first_role_user.meeting.id)

    db.session.add(first_job)
    db.session.add(second_job)
    db.session.commit()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = first_role_user.user.id

        resp = client.get(url_for('meetings.processing_file_list',
                                  meeting_id=1))
        assert resp.status_code == 200
        html = PyQuery(resp.data)
        assert html('#job-list tr').length == 3


def test_superuser(app):
    first_role = RoleFactory(permissions=('view_participant',))
    second_role = RoleFactory(permissions=('view_participant',))
    first_role_user = RoleUserMeetingFactory(role=first_role)
    second_role_user = RoleUserMeetingFactory(role=second_role,
                                              meeting=first_role_user.meeting)
    first_role_user.user.is_superuser = True

    q = Queue(Job.PRINTOUTS_QUEUE, connection=redis_store._redis_client,
              default_timeout=1200)
    first_job_redis = q.enqueue(_process_short_list,
                                first_role_user.meeting.id,
                                'List of participants', 'verified')
    second_job_redis = q.enqueue(_process_short_list,
                                 first_role_user.meeting.id,
                                 'List of participants', 'verified')
    first_job = JobsFactory(id=first_job_redis.id,
                            user_id=first_role_user.user.id,
                            meeting_id=first_role_user.meeting.id)
    second_job = JobsFactory(id=second_job_redis.id,
                             user_id=second_role_user.user.id,
                             meeting_id=first_role_user.meeting.id)

    db.session.add(first_job)
    db.session.add(second_job)
    db.session.commit()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = first_role_user.user.id

        resp = client.get(url_for('meetings.processing_file_list',
                                  meeting_id=1))
        assert resp.status_code == 200
        html = PyQuery(resp.data)
        assert html('#job-list tr').length == 3


def test_authenticated_user(app):
    first_role = RoleFactory(permissions=('view_participant',))
    second_role = RoleFactory(permissions=('view_participant',))
    first_role_user = RoleUserMeetingFactory(role=first_role)
    second_role_user = RoleUserMeetingFactory(role=second_role,
                                              meeting=first_role_user.meeting)

    q = Queue(Job.PRINTOUTS_QUEUE, connection=redis_store._redis_client,
              default_timeout=1200)
    first_job_redis = q.enqueue(_process_short_list,
                                first_role_user.meeting.id,
                                'List of participants', 'verified')
    second_job_redis = q.enqueue(_process_short_list,
                                 first_role_user.meeting.id,
                                 'List of participants', 'verified')
    first_job = JobsFactory(id=first_job_redis.id,
                            user_id=first_role_user.user.id,
                            meeting_id=first_role_user.meeting.id)
    second_job = JobsFactory(id=second_job_redis.id,
                             user_id=second_role_user.user.id,
                             meeting_id=first_role_user.meeting.id)

    db.session.add(first_job)
    db.session.add(second_job)
    db.session.commit()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = first_role_user.user.id

        resp = client.get(url_for('meetings.processing_file_list',
                                  meeting_id=1))
        assert resp.status_code == 200
        html = PyQuery(resp.data)
        assert html('#job-list tr').length == 2


def test_anonymous_user(app, user):
    role = RoleFactory(permissions=('',))
    role_user = RoleUserMeetingFactory(role=role)

    q = Queue(Job.PRINTOUTS_QUEUE, connection=redis_store._redis_client,
              default_timeout=1200)
    job_redis = q.enqueue(_process_short_list, role_user.meeting.id,
                          'List of participants', 'verified')
    job = JobsFactory(id=job_redis.id, user_id=role_user.user.id,
                      meeting_id=role_user.meeting.id)
    role_user.user.active = False
    db.session.add(job)
    db.session.commit()

    client = app.test_client()
    with app.test_request_context():
        with client.session_transaction() as sess:
            sess['user_id'] = role_user.user.id

        resp = client.get(url_for('meetings.processing_file_list',
                                  meeting_id=1))
        assert resp.status_code == 403
