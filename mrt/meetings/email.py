from flask import render_template, request, flash, redirect, url_for
from flask.views import MethodView

from mrt.forms.meetings.email import BulkEmailForm
from mrt.mail import send_bulk_message, send_single_message
from mrt.models import Participant, MailLog
from mrt.meetings.mixins import PermissionRequiredMixin


def get_recipients(language, categories=None, participant_type=None):
    """ Return a queryset of participants filtered by language and categories
    """
    queryset = (Participant.query.current_meeting()
                .filter_by(language=language))
    if categories:
        queryset = queryset.filter(Participant.category_id.in_(categories))
    if participant_type:
        queryset = queryset.filter_by(participant_type=participant_type)
    return queryset


class BulkEmail(PermissionRequiredMixin, MethodView):

    template_name = 'meetings/email/bulk.html'
    permission_required = ('manage_meeting', 'manage_participant')

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
        categories = request.args.getlist('categories[]')
        participant_type = request.args.get('participant_type')
        qs = get_recipients(language, categories, participant_type)
        return '{0}'.format(qs.count())


class RecipientsBulkList(MethodView):

    template_name = 'meetings/email/list_bulk.html'

    def get(self):
        language = request.args.get('language')
        categories = request.args.getlist('categories[]')
        participant_type = request.args.get('participant_type')
        qs = get_recipients(language, categories, participant_type)
        return render_template(self.template_name, participants=qs)


class ResendEmail(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', 'manage_participant')

    def post(self, mail_id):
        mail = MailLog.query.get_or_404(mail_id)
        if send_single_message(mail.to.email, mail.subject, mail.message):
            flash('Message successfully resent', 'success')
        else:
            flash('Message failed to send', 'error')

        return redirect(url_for('.mail_detail',
                                mail_id=mail.id))
