from flask import render_template
from flask.views import MethodView

from mrt.forms import MeetingEditForm

class MeetingAdd(MethodView):

    def get(self):
        form = MeetingEditForm()
        return render_template('meetings/add.html', form=form)
