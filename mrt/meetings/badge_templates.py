from flask import render_template, jsonify, g
from flask.views import MethodView

from mrt.meetings.mixins import PermissionRequiredMixin
from mrt.models import db


class BadgeTemplates(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting',)

    def get(self):
        return render_template('meetings/badge_templates/list.html')

    def post(self, badge_template):
        settings = dict(g.meeting.settings)
        settings['badge_template'] = badge_template
        g.meeting.settings = settings
        db.session.commit()
        return jsonify({'status': 'success'})
