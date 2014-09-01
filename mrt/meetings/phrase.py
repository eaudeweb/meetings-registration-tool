from flask import g
from flask import render_template, request, flash
from flask.ext.login import login_required
from flask.views import MethodView

from mrt.forms.admin import PhraseEditForm
from mrt.meetings import PermissionRequiredMixin
from mrt.models import Phrase


class PhraseEdit(PermissionRequiredMixin, MethodView):

    decorators = (login_required,)
    permission_required = ('manage_phrases', )

    def get(self, meeting_type, phrase_id=None):
        phrases = (Phrase.query.filter(Phrase.meeting == g.meeting)
                   .order_by(Phrase.group, Phrase.sort))
        if phrase_id:
            phrase = Phrase.query.get_or_404(phrase_id)
        else:
            phrase = phrases.first_or_404()
        form = PhraseEditForm(obj=phrase)
        return render_template('meetings/phrase/edit.html',
                               phrases=phrases,
                               form=form)

    def post(self, meeting_type, phrase_id=None):
        phrases = (Phrase.query.filter(Phrase.meeting == g.meeting)
                   .order_by(Phrase.group, Phrase.sort))
        if phrase_id:
            phrase = Phrase.query.get_or_404(phrase_id)
        else:
            phrase = phrases.first_or_404()
        form = PhraseEditForm(request.form, obj=phrase)
        if form.validate():
            form.save()
            flash('Phrase successfully updated', 'success')
        return render_template('meetings/phrase/edit.html',
                               phrases=phrases,
                               form=form)
