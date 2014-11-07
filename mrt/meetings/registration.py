from functools import wraps
from flask.views import MethodView
from flask import g, render_template, request, session, abort
from flask import redirect, url_for
from flask.ext.login import login_user, logout_user, current_user

from mrt.forms.auth import LoginForm
from mrt.forms.meetings import custom_form_factory, custom_object_factory
from mrt.forms.meetings import RegistrationForm, RegistrationUserForm
from mrt.models import Participant, db

from mrt.signals import activity_signal, notification_signal
from mrt.signals import registration_signal
from mrt.utils import set_language


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
        lang = request.args.get('lang', 'en')
        if lang in ('en', 'fr', 'es'):
            set_language(lang)
        Form = custom_form_factory(registration_fields=True,
                                   form=RegistrationForm)
        form = Form()
        if current_user.is_authenticated():
            participant = current_user.get_default()
            Object = custom_object_factory(participant)
            form = Form(obj=Object())
        return render_template('meetings/registration/form.html',
                               form=form)

    def post(self):
        Form = custom_form_factory(registration_fields=True,
                                   form=RegistrationForm)
        form = Form(request.form)
        if form.validate():
            participant = form.save()
            if current_user.is_authenticated():
                participant.user = current_user
                default_participant = current_user.get_default()
                if default_participant:
                    default_participant.update(participant)
            db.session.commit()

            activity_signal.send(self, participant=participant,
                                 action='add')
            notification_signal.send(self, participant=participant)
            registration_signal.send(self, participant=participant)

            user_form = RegistrationUserForm(email=participant.email)
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

        form = RegistrationUserForm(request.form)
        if form.validate():
            session.pop('registration_token', None)
            participant.user = form.save()
            db.session.flush()
            participant.clone()
            db.session.commit()
            return render_template('meetings/registration/user_success.html')
        return render_template('meetings/registration/success.html',
                               participant=participant,
                               form=form)


class UserRegistrationLogin(MethodView):

    def get(self):
        form = LoginForm()
        return render_template('meetings/registration/user_login.html',
                               form=form)

    def post(self):
        form = LoginForm(request.form)
        if form.validate():
            user = form.get_user()
            login_user(user)
            return redirect(url_for('meetings.registration'))
        return render_template('meetings/registration/user_login.html',
                               form=form)


class UserRegistrationLogout(MethodView):

    def get(self):
        logout_user()
        return redirect(url_for('.registration'))
