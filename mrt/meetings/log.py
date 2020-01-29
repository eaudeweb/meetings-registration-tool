from flask import g, render_template, request
from flask.views import MethodView

from blinker import ANY
from datetime import datetime, timedelta

from mrt.models import db, Category, ActivityLog, MailLog, Participant
from mrt.meetings.mixins import PermissionRequiredMixin
from mrt.signals import activity_signal
from mrt.definitions import LANGUAGES_ORDERED_LIST


@activity_signal.connect_via(ANY)
def activity_listener(sender, participant, action, staff=None):
    activity = ActivityLog(participant=participant,
                           meeting=participant.meeting,
                           staff=staff, action=action,
                           date=datetime.now())
    db.session.add(activity)
    db.session.commit()


class Integration(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', )
    template_name = 'meetings/overview/integration.html'

    def get(self):
        return render_template(self.template_name, languages=LANGUAGES_ORDERED_LIST)


class Statistics(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', )
    template_name = 'meetings/overview/statistics.html'

    def get(self):
        participant_categories = (
            Category.get_categories_for_meeting(Category.PARTICIPANT))
        media_categories = Category.get_categories_for_meeting(Category.MEDIA)
        total_delegates = sum(category.participants.filter_by(deleted=False).count()
                                    for category in participant_categories)

        return render_template(
            self.template_name,
            participant_categories=participant_categories,
            media_categories=media_categories,
            total_delegates=total_delegates,
            sex_field=(
                g.meeting.custom_fields.filter_by(slug='sex').scalar()
            ),
            female_delegates=(
                g.meeting.participants.filter_by(
                    sex=Participant.SEX_CHOICES[0][0]
                ).count()
            ),
            male_delegates=(
                g.meeting.participants.filter_by(
                    sex=Participant.SEX_CHOICES[1][0]
                ).count()
            ),
            neutral_delegates=(
                g.meeting.participants.filter_by(
                    sex=Participant.SEX_CHOICES[2][0]
                ).count()
            )
        )


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
        activities = g.meeting.activities.order_by(ActivityLog.date.desc())
        staff_members = [activity.staff for activity in
                         g.meeting.activities.distinct(ActivityLog.staff_id)]

        staff_id = request.args.get('staff_id', None, type=int)
        seconds = request.args.get('time', None, type=int)
        part_id = request.args.get('part_id', None, type=int)
        action = request.args.get('action', None)

        if staff_id is not None:
            activities = activities.filter_by(staff_id=staff_id or None)

        if seconds:
            relative_date = datetime.now() - timedelta(seconds=seconds)
            activities = activities.filter(ActivityLog.date > relative_date)

        if part_id:
            activities = activities.filter_by(participant_id=part_id)

        if action:
            activities = activities.filter_by(action=action)

        return render_template('meetings/log/activity.html',
                               activities=activities,
                               staff_id=staff_id,
                               staff_members=staff_members,
                               seconds=seconds,
                               part_id=part_id,
                               action=action)
