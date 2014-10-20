from flask.views import MethodView
from flask import render_template, request

from mrt.forms.meetings import custom_form_factory
from mrt.forms.meetings import RegistrationForm


class Registration(MethodView):

    def get(self):
        Form = custom_form_factory(registration_fields=True,
                                   form=RegistrationForm)
        form = Form()
        return render_template('meetings/registration/form.html',
                               form=form)

    def post(self):
        Form = custom_form_factory(registration_fields=True,
                                   form=RegistrationForm)
        form = Form(request.form)
        if form.validate():
            form.save()
        return render_template('meetings/registration/form.html',
                               form=form)
