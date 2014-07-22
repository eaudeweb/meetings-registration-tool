from flask import request, redirect, render_template, jsonify
from flask import url_for
from flask import flash
from flask.views import MethodView

from mrt.models import Meeting, db
from mrt.forms import MeetingEditForm


class Meetings(MethodView):

    def get(self):
        meetings = Meeting.query.all()
        return render_template('meetings/meeting/list.html',
                               meetings=meetings)


class MeetingEdit(MethodView):

    def get(self, meeting_id=None):
        if meeting_id:
            meeting = Meeting.query.get_or_404(meeting_id)
        else:
            meeting = None
        form = MeetingEditForm(obj=meeting)
        return render_template('meetings/meeting/edit.html',
                               form=form, meeting=meeting)

    def post(self, meeting_id=None):
        if meeting_id:
            meeting = Meeting.query.get_or_404(meeting_id)
        else:
            meeting = None
        form = MeetingEditForm(request.form, obj=meeting)
        if form.validate():
            form.save()
            if meeting_id:
                flash('Meeting successfully added', 'success')
            else:
                flash('Meeting successfully updated', 'success')
            return redirect(url_for('.home'))
        return render_template('meetings/meeting/edit.html', form=form)

    def delete(self, meeting_id=None):
        meeting = Meeting.query.get_or_404(meeting_id)
        db.session.delete(meeting)
        db.session.commit()
        return jsonify(status="success", url=url_for('.home'))
