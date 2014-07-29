from flask import flash, redirect, url_for
from flask import render_template
from flask import request
from flask.views import MethodView
from flask.ext.login import login_required

from mrt.models import PhraseDefault
from mrt.definitions import MEETING_TYPES
from mrt.forms.admin import PhraseEditForm


class PhrasesTypes(MethodView):

    decorators = (login_required,)

    def get(self):
        return render_template('admin/phrase/list.html',
                               meeting_types=MEETING_TYPES)


class PhraseEdit(MethodView):

    decorators = (login_required,)

    def get(self, meeting_type, phrase_id=None):
        phrases = (
            PhraseDefault.query
            .filter_by(meeting_type=meeting_type)
            .order_by(PhraseDefault.group, PhraseDefault.sort))
        if phrase_id:
            phrase = PhraseDefault.query.get_or_404(phrase_id)
        else:
            phrase = phrases.first_or_404()
            return redirect(url_for('.phrase_edit',
                                    meeting_type=phrase.meeting_type.code,
                                    phrase_id=phrase.id))

        form = PhraseEditForm(obj=phrase)
        return render_template('admin/phrase/edit.html',
                               phrases=phrases, phrase=phrase, form=form)

    def post(self, meeting_type, phrase_id):
        phrase = PhraseDefault.query.get_or_404(phrase_id)
        form = PhraseEditForm(request.form, obj=phrase)
        if form.validate():
            form.save()
            flash('Default phrase successfully updated', 'success')
        phrases = (
            PhraseDefault.query
            .filter_by(meeting_type=meeting_type)
            .order_by(PhraseDefault.group, PhraseDefault.sort))
        return render_template('admin/phrase/edit.html',
                               phrases=phrases, phrase=phrase, form=form)
