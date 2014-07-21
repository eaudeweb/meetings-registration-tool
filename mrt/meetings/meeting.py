from flask import request, redirect, render_template
from flask import url_for
from flask.views import MethodView

from mrt.models import Meeting
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
        return render_template('meetings/edit.html',
                               form=form, meeting=meeting)

    def post(self, meeting_id=None):
        if meeting_id:
            meeting = Meeting.query.get_or_404(meeting_id)
        else:
            meeting = None
        form = MeetingEditForm(request.form, obj=meeting)
        if form.validate():
            form.save()
            return redirect(url_for('.home'))
        return render_template('meetings/edit.html', form=form)
