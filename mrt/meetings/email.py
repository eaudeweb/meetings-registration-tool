from flask import render_template, request, flash, redirect, url_for, jsonify
from flask.views import MethodView

from mrt.forms.meetings.email import BulkEmailForm
from mrt.models import Participant


def get_recipients(language, categories=None):
    """ Return a queryset of participants filtered by language and categories
    """
    queryset = Participant.query.filter_by(language=language)
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
            print form.data
            flash('Bulk messages sent', 'success')
            return redirect(url_for('.bulkemail'))
        return render_template(self.template_name, form=form)


class RecipientsCount(MethodView):

    def get(self):
        language = request.args.get('language')
        categories = request.args.get('categories[]')
        qs = get_recipients(language, categories)
        return '{0}'.format(qs.count())
