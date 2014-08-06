from flask import g, request, redirect, url_for, jsonify
from flask import render_template, flash
from flask.views import MethodView

from werkzeug.utils import HTMLBuilder

from mrt.forms.meetings import ParticipantEditForm
from mrt.mixins import FilterView
from mrt.models import db, Participant


class Participants(MethodView):

    def get(self):
        return render_template('meetings/participant/list.html')


class ParticipantsFilter(MethodView, FilterView):

    def process_last_name(self, participant, val):
        html = HTMLBuilder('html')
        url = url_for('.participant_detail', participant_id=participant.id)
        return html.a(participant.name, href=url)

    def process_category_id(self, participant, val):
        return str(participant.category)

    def get_queryset(self, **opt):
        participants = Participant.query.filter_by(meeting_id=g.meeting.id)
        total = participants.count()

        for item in opt['order']:
            participants = participants.order_by(
                '%s %s' % (item['column'], item['dir']))

        if opt['search']:
            participants = (
                participants.filter(
                    Participant.first_name.contains(opt['search']) |
                    Participant.last_name.contains(opt['search']) |
                    Participant.email.contains(opt['search'])
                )
            )

        participants = participants.limit(opt['limit']).offset(opt['start'])
        return participants, total


class ParticipantDetail(MethodView):

    def get(self, participant_id):
        participant = (
            Participant.query
            .filter_by(meeting_id=g.meeting.id, id=participant_id)
            .first_or_404())
        form = ParticipantEditForm(obj=participant)
        return render_template('meetings/participant/detail.html',
                               participant=participant,
                               form=form)


class ParticipantEdit(MethodView):

    def _get_object(self, participant_id=None):
        return (Participant.query
                .filter_by(meeting_id=g.meeting.id, id=participant_id)
                .first_or_404()
                if participant_id else None)

    def get(self, participant_id=None):
        participant = self._get_object(participant_id)
        form = ParticipantEditForm(obj=participant)
        return render_template('meetings/participant/edit.html',
                               form=form,
                               participant=participant)

    def post(self, participant_id=None):
        participant = self._get_object(participant_id)
        form = ParticipantEditForm(request.form, obj=participant)
        if form.validate():
            form.save()
            flash('Person information saved', 'success')
            return redirect(url_for('.participants'))
        return render_template('meetings/participant/edit.html',
                               form=form,
                               participant=participant)

    def delete(self, participant_id):
        participant = self._get_object(participant_id)
        db.session.delete(participant)
        db.session.commit()
        flash('Participant successfully deleted', 'warning')
        return jsonify(status="success", url=url_for('.participants'))
