from flask import g, render_template
from flask import jsonify, flash, url_for, request
from flask.views import MethodView

from blinker import ANY
from datetime import datetime, timedelta

from mrt.models import db, Participant, MediaParticipant
from mrt.models import ActivityLog, MailLog, RoleUser
from mrt.meetings import PermissionRequiredMixin
from mrt.signals import activity_signal


@activity_signal.connect_via(ANY)
def activity_listener(sender, participant, action, staff=None):
    activity = ActivityLog(participant=participant,
                           meeting=participant.meeting,
                           staff=staff, action=action,
                           date=datetime.now())
    db.session.add(activity)
    db.session.commit()


class Statistics(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', )

    def get(self):
        participants = (
            Participant.query.filter_by(meeting_id=g.meeting.id).active())
        media_participants = (
            MediaParticipant.query.filter_by(meeting_id=g.meeting.id))
        return render_template('meetings/log/statistics.html',
                               participants=participants,
                               media_participants=media_participants)


class MailLogs(PermissionRequiredMixin, MethodView):

    permission_required = ('view_participant', )

    def get(self):
        mails = MailLog.query.filter_by(meeting_id=g.meeting.id)
        return render_template('meetings/log/email/list.html',
                               mails=mails)


class MailLogDetail(PermissionRequiredMixin, MethodView):

    permission_required = ('view_participant', )

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


class ActivityLogs(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', )

    def get(self):
        staffs = RoleUser.query.filter_by(meeting=g.meeting)
        activities = ActivityLog.query.filter_by(meeting=g.meeting)

        staff_id = request.args.get('staff_id', None)
        seconds = request.args.get('time', None)
        part_id = request.args.get('part_id', None)
        action = request.args.get('action', None)

        if staff_id:
            activities = activities.filter_by(staff_id=int(staff_id))

        if seconds:
            relative_date = datetime.now() - timedelta(seconds=int(seconds))
            activities = activities.filter(ActivityLog.date > relative_date)

        if part_id:
            activities = activities.filter_by(participant_id=part_id)

        if action:
            activities = activities.filter_by(action=action)

        return render_template('meetings/log/activity.html',
                               activities=activities,
                               staffs=staffs,
                               staff_id=staff_id,
                               seconds=seconds,
                               part_id=part_id,
                               action=action)
