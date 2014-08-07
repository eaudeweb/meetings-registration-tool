from flask import g, url_for
from flask import render_template
from flask.views import MethodView

from werkzeug.utils import HTMLBuilder

from mrt.mixins import FilterView
from mrt.models import MediaParticipant


class MediaParticipants(MethodView):

    def get(self):
        return render_template('meetings/media_participant/list.html')


class MediaParticipantsFilter(MethodView, FilterView):

    def process_last_name(self, media_participant, val):
        html = HTMLBuilder('html')
        url = url_for('.media_participant_detail',
                      media_participant_id=media_participant.id)
        return html.a(media_participant.name, href=url)

    def process_category_id(self, media_participant, val):
        return str(media_participant.category)

    def get_queryset(self, **opt):
        media_participants = MediaParticipant.query.filter_by(
            meeting_id=g.meeting.id)
        total = media_participants.count()

        for item in opt['order']:
            media_participants = media_participants.order_by(
                '%s %s' % (item['column'], item['dir']))

        if opt['search']:
            media_participants = (
                media_participants.filter(
                    MediaParticipant.first_name.contains(opt['search']) |
                    MediaParticipant.last_name.contains(opt['search']) |
                    MediaParticipant.email.contains(opt['search'])
                )
            )

        media_participants = media_participants.limit(opt['limit']).offset(
            opt['start'])
        return media_participants, total


class MediaParticipantDetail(MethodView):

    def get(self, media_participant_id):
        media_participant = (
            MediaParticipant.query
            .filter_by(meeting_id=g.meeting.id, id=media_participant_id)
            .first_or_404())
        return render_template('meetings/media_participant/detail.html',
                               media_participant=media_participant)
