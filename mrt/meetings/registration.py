from functools import wraps
from flask.views import MethodView
from flask import g, render_template, request, session, abort

from mrt.models import Participant, db
from mrt.forms.meetings import custom_form_factory
from mrt.forms.meetings import RegistrationForm
from mrt.forms.auth import UserRegistrationForm
from mrt.signals import activity_signal, notification_signal
from mrt.signals import registration_signal


def _render_if_closed(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not g.meeting.online_registration:
            return render_template('meetings/registration/closed.html')
        return func(*args, **kwargs)
    return wrapper


class Registration(MethodView):

    decorators = (_render_if_closed,)

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
            participant = form.save()
            activity_signal.send(self, participant=participant,
                                 action='add')
            notification_signal.send(self, participant=participant)
            registration_signal.send(self, participant=participant)

            user_form = UserRegistrationForm(email=participant.email)
            session['registration_token'] = participant.registration_token

            return render_template('meetings/registration/success.html',
                                   participant=participant,
                                   form=user_form)
        return render_template('meetings/registration/form.html',
                               form=form)


class UserRegistration(MethodView):

    def post(self):
        registration_token = session.get('registration_token', None)
        if not registration_token:
            abort(400)
        participant = Participant.query.filter_by(
            registration_token=registration_token).first_or_404()

        form = UserRegistrationForm(request.form)
        if form.validate():
            session.pop('registration_token', None)
            participant.user = form.save()
            db.session.commit()
        return render_template('meetings/registration/success.html',
                               participant=participant,
                               form=form)
