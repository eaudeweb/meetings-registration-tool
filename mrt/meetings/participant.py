from flask import g
from flask import render_template
from flask.views import MethodView
from mrt.models import Participant


class Participants(MethodView):

    def get(self):
        return render_template('meetings/participant/list.html')


class ParticipantEdit(MethodView):

    def _get_object(self, participant_id=None):
        return (Participant.query
                .filter(meeting_id=g.meeting.id, id=participant_id)
                .first_or_404()
                if participant_id else None)

    def get(self, participant_id=None):
        participant = self._get_object()
        return render_template('meetings/participant/edit.html',
                               participant=participant)

    def post(self, participant_id):
        participant = self._get_object()
        return render_template('meetings/participant/edit.html',
                               participant=participant)
