from flask import g, render_template
from flask import jsonify, flash, url_for
from flask.views import MethodView
from flask.ext.login import current_user as user

from blinker import ANY
from datetime import datetime

from mrt.models import db, Participant, MediaParticipant
from mrt.models import ActivityLog, MailLog, Staff
from mrt.signals import activity_signal


@activity_signal.connect_via(ANY)
def activity_listener(sender, participant, action):
    staff = Staff.query.filter_by(user=user).first()
    activity = ActivityLog(participant_name=participant.first_name,
                           participant_id=participant.id,
                           meeting=participant.meeting,
                           staff=staff, action=action,
                           date=datetime.now())
    db.session.add(activity)
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
        activities = ActivityLog.query.filter_by(meeting=g.meeting)
        return render_template('meetings/log/activity.html',
                               activities=activities)
