from flask import g, render_template, request
from flask.views import MethodView

from blinker import ANY
from datetime import datetime, timedelta
from sqlalchemy import or_

from mrt.models import db, Participant
from mrt.models import ActivityLog, MailLog, RoleUser
from mrt.meetings.mixins import PermissionRequiredMixin
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
        query = Participant.query.current_meeting()
        participants = query.participants()
        media_participants = query.media_participants()
        return render_template('meetings/overview/statistics.html',
                               participants=participants,
                               media_participants=media_participants)


class MailLogs(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', 'manage_participant')

    def get(self):
        mails = (MailLog.query.filter_by(meeting_id=g.meeting.id)
                 .order_by(MailLog.date_sent.desc()))
        return render_template('meetings/log/email/list.html',
                               mails=mails)


class MailLogDetail(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', 'manage_participant')

    def get(self, mail_id):
        mail = MailLog.query.get_or_404(mail_id)
        return render_template('meetings/log/email/detail.html',
                               mail=mail)


class ActivityLogs(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', )

    def get(self):
        staffs = (
            RoleUser.query
            .filter(or_(RoleUser.meeting == g.meeting,
                        RoleUser.meeting == None))
            .distinct(RoleUser.user_id).all())
        activities = g.meeting.activities.order_by(ActivityLog.date.desc())

        staff_id = request.args.get('staff_id', None)
        seconds = request.args.get('time', None)
        part_id = request.args.get('part_id', None)
        action = request.args.get('action', None)

        if staff_id:
            staff_id = None if int(staff_id) == 0 else int(staff_id)
            activities = activities.filter_by(staff_id=staff_id)

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
