from flask import render_template, request, flash, redirect, url_for, g, abort
from flask.views import MethodView

from mrt.forms.meetings.email import BulkEmailForm, AckEmailForm
from mrt.mail import send_bulk_message, send_single_message
from mrt.models import Participant


def get_recipients(language, categories=None):
    """ Return a queryset of participants filtered by language and categories
    """
    queryset = Participant.active_query.filter_by(meeting=g.meeting,
                                                  language=language)
    if categories:
        queryset = queryset.filter(Participant.category_id.in_(categories))
    return queryset


class BulkEmail(MethodView):

    template_name = 'meetings/email/bulk.html'

    def get(self):
        form = BulkEmailForm()
        return render_template(self.template_name, form=form)

    def post(self):
        form = BulkEmailForm(request.form)

        if form.validate():
            recipients = get_recipients(form.language.data,
                                        form.categories.data)
            if recipients:
                sent = send_bulk_message(
                    recipients,
                    subject=form.subject.data,
                    message=form.message.data,
                )
                if sent > 0:
                    flash('Bulk messages sent', 'success')
            else:
                flash('No recipients.', 'error')
            return redirect(url_for('.bulkemail'))
        return render_template(self.template_name, form=form)


class RecipientsCount(MethodView):

    def get(self):
        language = request.args.get('language')
        categories = request.args.get('categories[]')
        qs = get_recipients(language, categories)
        return '{0}'.format(qs.count())


class AckEmail(MethodView):

    template_name = 'meetings/email/ack.html'

    def get_participant(self, participant_id):
        return (
            Participant.active_query
            .filter_by(meeting=g.meeting, id=participant_id)
            .first()
        ) or abort(404)

    def get(self, participant_id):
        participant = self.get_participant(participant_id)
        form = AckEmailForm(to=participant.email)
        return render_template(self.template_name, participant=participant,
                               form=form)

    def post(self, participant_id):
        participant = self.get_participant(participant_id)
        form = AckEmailForm(request.form)
        if form.validate():
            if send_single_message(form.to.data, form.subject.data,
                                   form.message.data):
                flash('Message successfully sent', 'success')
                return redirect(
                    url_for('.participant_detail',
                            participant_id=participant.id)
                )
            else:
                flash('Message failed do send', 'error')

        return render_template(self.template_name, participant=participant,
                               form=form)
