from flask import request, redirect, render_template, jsonify
from flask import url_for, flash
from flask.views import MethodView
from flask.ext.login import login_required

from mrt.models import Meeting, db
from mrt.forms import MeetingEditForm


class Meetings(MethodView):

    decorators = (login_required, )

    def get(self):
        meetings = Meeting.query.all()
        return render_template('meetings/meeting/list.html',
                               meetings=meetings)


class MeetingEdit(MethodView):

    decorators = (login_required, )

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
                flash('Meeting successfully updated', 'success')
            else:
                flash('Meeting successfully added', 'success')
            return redirect(url_for('.home'))
        flash('Meeting was not saved. Please see the errors bellow', 'danger')
        return render_template('meetings/meeting/edit.html', form=form)

    def delete(self, meeting_id=None):
        meeting = Meeting.query.get_or_404(meeting_id)
        db.session.delete(meeting)
        db.session.commit()
        flash('Meeting successfully deleted', 'warning')
        return jsonify(status="success", url=url_for('.home'))
