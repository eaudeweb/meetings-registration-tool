from flask import flash
from flask import render_template
from flask import request, redirect, url_for
from flask.ext.login import login_required
from flask.views import MethodView

from mrt.admin.mixins import PermissionRequiredMixin
from mrt.forms.admin import PhraseDefaultEditForm
from mrt.models import PhraseDefault, MeetingType


class PhrasesTypes(PermissionRequiredMixin, MethodView):

    decorators = (login_required,)

    def get(self):
        m_types = [(m.slug, m.label) for m in MeetingType.query.ignore_def()]
        return render_template('admin/phrase/list.html', meeting_types=m_types)


class PhraseEdit(PermissionRequiredMixin, MethodView):

    decorators = (login_required,)

    def get(self, meeting_type, phrase_id=None):
        phrases = (
            PhraseDefault.query
            .filter_by(meeting_type_slug=meeting_type)
            .order_by(PhraseDefault.group, PhraseDefault.sort))
        if phrase_id:
            phrase = PhraseDefault.query.get_or_404(phrase_id)
        else:
            phrase = phrases.first_or_404()
            return redirect(url_for('.phrase_edit',
                                    meeting_type=meeting_type,
                                    phrase_id=phrase.id))
        form = PhraseDefaultEditForm(obj=phrase)
        return render_template('admin/phrase/edit.html',
                               phrases=phrases, phrase=phrase, form=form)

    def post(self, meeting_type, phrase_id=None):
        phrases = (
            PhraseDefault.query
            .filter_by(meeting_type_slug=meeting_type)
            .order_by(PhraseDefault.group, PhraseDefault.sort))
        if phrase_id:
            phrase = PhraseDefault.query.get_or_404(phrase_id)
        else:
            phrase = phrases.first_or_404()
            return redirect(url_for('.phrase_edit',
                                    meeting_type=meeting_type,
                                    phrase_id=phrase.id))
        form = PhraseDefaultEditForm(request.form, obj=phrase)
        if form.validate():
            form.save()
            flash('Default phrase successfully updated', 'success')
        return render_template('admin/phrase/edit.html',
                               phrases=phrases, phrase=phrase, form=form)
