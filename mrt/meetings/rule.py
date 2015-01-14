from flask.views import MethodView
from flask import render_template


class Rules(MethodView):

    def get(self):
        pass


class RuleEdit(MethodView):

    def get(self):
        return render_template('meetings/rule/edit.html')

    def post(self):
        pass
