from flask import request, redirect, render_template
from flask import url_for
from flask.views import MethodView

from mrt.forms import MeetingEditForm


class MeetingList(MethodView):

    def get(self):
        return render_template('meetings/list.html')


class MeetingEdit(MethodView):

    def get(self, meeting_id=None):
        form = MeetingEditForm()
        return render_template('meetings/edit.html', form=form)

    def post(self, meeting_id=None):
        form = MeetingEditForm(request.form)
        if form.validate():
            form.save()
            return redirect(url_for('.list'))
        return render_template('meetings/edit.html', form=form)
