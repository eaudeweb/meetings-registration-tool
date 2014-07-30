from flask import g, request
from flask import render_template
from flask.views import MethodView

from mrt.models import Participant
from mrt.forms.meetings import ParticipantEditForm


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
        form = ParticipantEditForm(obj=participant)
        return render_template('meetings/participant/edit.html',
                               form=form,
                               participant=participant)

    def post(self, participant_id=None):
        participant = self._get_object()
        form = ParticipantEditForm(request.form, obj=participant)
        if form.validate():
          form.save()
        return render_template('meetings/participant/edit.html',
                               form=form,
                               participant=participant)
