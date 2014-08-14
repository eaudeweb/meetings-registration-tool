from flask import g, render_template
from flask import jsonify, flash, url_for, request
from flask.views import MethodView
from flask.ext.login import current_user as user

from blinker import ANY
from datetime import datetime, timedelta

from mrt.models import db, Participant, MediaParticipant
from mrt.models import ActivityLog, MailLog, Staff, RoleUser
from mrt.signals import activity_signal


@activity_signal.connect_via(ANY)
def activity_listener(sender, participant, action):
    staff = Staff.query.filter_by(user=user).first()
    activity = ActivityLog(participant_name=participant.name,
                           participant_id=participant.id,
                           meeting=participant.meeting,
                           staff=staff, action=action,
                           date=datetime.now())
    db.session.add(activity)
    if action == 'delete':
        activity.participant_id = None
        query = ActivityLog.query.filter_by(participant_id=participant.id)
        query.update({ActivityLog.participant_id: None})
    db.session.commit()


class Statistics(MethodView):

    def get(self):
        participants = Participant.query.filter_by(meeting_id=g.meeting.id)
        media_participants = (
            MediaParticipant.query.filter_by(meeting_id=g.meeting.id))
        return render_template('meetings/log/statistics.html',
                               participants=participants,
                               media_participants=media_participants)


class MailLogs(MethodView):

    def get(self):
        mails = MailLog.query.filter_by(meeting_id=g.meeting.id)
        return render_template('meetings/log/email/list.html',
                               mails=mails)


class MailLogDetail(MethodView):

    def get(self, mail_id):
        mail = MailLog.query.get_or_404(mail_id)
        return render_template('meetings/log/email/detail.html',
                               mail=mail)

    def delete(self, mail_id):
        mail = MailLog.query.get_or_404(mail_id)
        db.session.delete(mail)
        db.session.commit()
        flash('Email log successfully deleted', 'warning')
        return jsonify(status="success", url=url_for('.mail_logs'))


class ActivityLogs(MethodView):

    def get(self):
        staffs = RoleUser.query.filter_by(meeting=g.meeting)
        activities = ActivityLog.query.filter_by(meeting=g.meeting)

        staff_id = request.args.get('staff_id', 0)
        seconds = request.args.get('time', 0)
        name = request.args.get('name', 0)

        if staff_id:
            activities = activities.filter_by(staff_id=int(staff_id))

        if seconds:
            relative_date = datetime.now() - timedelta(seconds=int(seconds))
            activities = activities.filter(ActivityLog.date > relative_date)

        if name:
            activities = activities.filter_by(participant_name=name)

        return render_template('meetings/log/activity.html',
                               activities=activities,
                               staffs=staffs)
