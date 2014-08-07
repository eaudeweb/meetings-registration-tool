from flask import render_template
from flask.views import MethodView

from mrt.forms.meetings.email import BulkEmailForm


class BulkEmail(MethodView):

    def get(self):
        form = BulkEmailForm()
        return render_template('meetings/email/bulk.html', form=form)
