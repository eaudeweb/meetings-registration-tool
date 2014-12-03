from flask import flash
from flask import render_template
from flask import request
from flask.views import MethodView
from flask.ext.login import login_required

from mrt.models import PhraseDefault
from mrt.definitions import MEETING_TYPES
from mrt.forms.admin import PhraseDefaultEditForm
from mrt.meetings import PermissionRequiredMixin


class PhrasesTypes(PermissionRequiredMixin, MethodView):

    decorators = (login_required,)
    permission_required = ('manage_default', )

    def get(self):
        return render_template('admin/phrase/list.html',
                               meeting_types=MEETING_TYPES)


class PhraseEdit(PermissionRequiredMixin, MethodView):

    decorators = (login_required,)
    permission_required = ('manage_default', )

    def get(self, meeting_type, phrase_id=None):
        phrases = (
            PhraseDefault.query
            .filter_by(meeting_type_slug=meeting_type)
            .order_by(PhraseDefault.group, PhraseDefault.sort))
        if phrase_id:
            phrase = PhraseDefault.query.get_or_404(phrase_id)
        else:
            phrase = phrases.first_or_404()
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
        form = PhraseDefaultEditForm(request.form, obj=phrase)
        if form.validate():
            form.save()
            flash('Default phrase successfully updated', 'success')
        return render_template('admin/phrase/edit.html',
                               phrases=phrases, phrase=phrase, form=form)
