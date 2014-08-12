from flask import g, render_template
from flask.views import MethodView

from mrt.models import Participant, MediaParticipant


class Statistics(MethodView):

    def get(self):
        participants = Participant.query.filter_by(meeting_id=g.meeting.id)
        media_participants = (
            MediaParticipant.query.filter_by(meeting_id=g.meeting.id))
        return render_template('meetings/log/statistics.html',
                               participants=participants,
                               media_participants=media_participants)
