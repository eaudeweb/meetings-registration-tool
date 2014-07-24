from flask import render_template
from flask.views import MethodView


class Participants(MethodView):

    def get(self):
        return render_template('meetings/participant/list.html')
