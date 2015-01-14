from flask.views import MethodView
from flask import render_template
from mrt.forms.meetings import RuleForm


class Rules(MethodView):

    def get(self):
        pass


class RuleEdit(MethodView):

    def get(self):
        form = RuleForm()
        return render_template('meetings/rule/edit.html', form=form)

    def post(self):
        pass
