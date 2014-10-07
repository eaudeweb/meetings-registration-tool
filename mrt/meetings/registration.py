from flask.views import MethodView
from flask import render_template, request

from mrt.forms.meetings import RegistrationForm


class Registration(MethodView):

    def get(self):
        form = RegistrationForm()
        return render_template('meetings/registration/form.html',
                               form=form)

    def post(self):
        form = RegistrationForm(request.form)
        if form.validate():
            form.save()
        return render_template('meetings/registration/form.html',
                               form=form)
