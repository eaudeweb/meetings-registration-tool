from flask import g, url_for, flash, jsonify
from flask import render_template, request, redirect
from flask.views import MethodView

from werkzeug.utils import HTMLBuilder

from mrt.forms.meetings import MediaParticipantEditForm
from mrt.meetings import PermissionRequiredMixin
from mrt.mixins import FilterView
from mrt.models import db, MediaParticipant
from mrt.signals import notification_signal


class MediaParticipants(PermissionRequiredMixin, MethodView):

    permission_required = ('view_media_participant',)

    def get(self):
        return render_template('meetings/media_participant/list.html')


class MediaParticipantsFilter(PermissionRequiredMixin, MethodView, FilterView):

    permission_required = ('view_media_participant',)

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


class MediaParticipantDetail(PermissionRequiredMixin, MethodView):

    permission_required = ('view_media_participant', )

    def get(self, media_participant_id):
        media_participant = (
            MediaParticipant.query
            .filter_by(meeting_id=g.meeting.id, id=media_participant_id)
            .first_or_404())
        form = MediaParticipantEditForm(obj=media_participant)
        return render_template('meetings/media_participant/detail.html',
                               media_participant=media_participant,
                               form=form)


class MediaParticipantEdit(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_media_participant', )

    def _get_object(self, media_participant_id=None):
        return (MediaParticipant.query
                .filter_by(meeting_id=g.meeting.id, id=media_participant_id)
                .first_or_404()
                if media_participant_id else None)

    def get(self, media_participant_id=None):
        media_participant = self._get_object(media_participant_id)
        form = MediaParticipantEditForm(obj=media_participant)
        return render_template('meetings/media_participant/edit.html',
                               form=form,
                               media_participant=media_participant)

    def post(self, media_participant_id=None):
        media_participant = self._get_object(media_participant_id)
        form = MediaParticipantEditForm(request.form, obj=media_participant)
        if form.validate():
            media_participant = form.save()
            flash('MediaParticipant information saved', 'success')
            notification_signal.send(self, participant=media_participant)
            return redirect(url_for('.media_participant_detail',
                                    media_participant_id=media_participant.id))
        return render_template('meetings/media_participant/edit.html',
                               form=form,
                               media_participant=media_participant)

    def delete(self, media_participant_id):
        media_participant = self._get_object(media_participant_id)
        db.session.delete(media_participant)
        db.session.commit()
        flash('Media participant successfully deleted', 'warning')
        return jsonify(status="success", url=url_for('.media_participants'))
