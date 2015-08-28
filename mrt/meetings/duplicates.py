from flask import render_template, request, flash, redirect, url_for, g
from flask.views import MethodView

from mrt.models import Participant

from mrt.meetings.mixins import PermissionRequiredMixin


def get_duplicates_by_email():
    groups = []
    participants = g.meeting.participants.filter_by(deleted=False)
    email_hash = {}

    for participant in participants:
        if participant.email in email_hash:
            email_hash[participant.email].append(participant)
        else:
            email_hash[participant.email] = [participant]

    for email in email_hash:
        if len(email_hash[email]) > 1:
            groups.append(email_hash[email])

    return groups


class ManageDuplicates(PermissionRequiredMixin, MethodView):

    template_name = 'meetings/duplicates/list.html'
    permission_required = ('manage_meeting', 'view_participant',
                           'manage_participant')

    def get(self):
        groups = get_duplicates_by_email()
        return render_template(self.template_name, groups=groups)
