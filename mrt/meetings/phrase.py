from flask import g
from flask import render_template, request, flash
from flask import url_for, redirect
from flask.ext.login import login_required
from flask.views import MethodView

from mrt.forms.admin import PhraseEditForm
from mrt.models import Phrase


class PhraseEdit(MethodView):

    decorators = (login_required,)

    def get(self, phrase_id=None):
        phrases = (Phrase.query.filter(Phrase.meeting == g.meeting)
                   .order_by(Phrase.group, Phrase.sort))
        if phrase_id:
            phrase = Phrase.query.get_or_404(phrase_id)
        else:
            phrase = phrases.first_or_404()
            return redirect(url_for('.phrase_edit', phrase_id=phrase.id))

        form = PhraseEditForm(obj=phrase)
        return render_template('meetings/phrase/edit.html',
                               phrases=phrases,
                               form=form)

    def post(self, phrase_id):
        phrase = Phrase.query.get_or_404(phrase_id)
        form = PhraseEditForm(request.form, obj=phrase)
        if form.validate():
            form.save()
            flash('Phrase successfully updated', 'success')
        phrases = (Phrase.query.filter(Phrase.meeting == g.meeting)
                   .order_by(Phrase.group, Phrase.sort))
        return render_template('meetings/phrase/edit.html',
                               phrases=phrases,
                               form=form)
