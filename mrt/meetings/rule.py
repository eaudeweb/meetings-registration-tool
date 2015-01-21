from flask import g, render_template, jsonify, abort, request
from flask import redirect, url_for
from flask.ext.login import login_required
from flask.views import MethodView

from mrt.forms.meetings import RuleForm
from mrt.meetings.mixins import PermissionRequiredMixin
from mrt.models import Category, CustomField, Rule
from mrt.utils import get_all_countries


class Rules(PermissionRequiredMixin, MethodView):

    decorators = (login_required,)
    permission_required = ('manage_meeting',)

    def get(self):
        rules = Rule.query.filter_by(meeting=g.meeting)
        return render_template('meetings/rule/list.html', rules=rules)


class RuleEdit(PermissionRequiredMixin, MethodView):

    decorators = (login_required,)
    permission_required = ('manage_meeting',)

    def get(self, rule_id=None):
        form = RuleForm()
        return render_template('meetings/rule/edit.html', form=form)

    def post(self, rule_id=None):
        form = RuleForm(request.form)
        if form.validate():
            form.save()
            return redirect(url_for('.rules'))
        return render_template('meetings/rule/edit.html', form=form)


class RulesData(PermissionRequiredMixin, MethodView):

    decorators = (login_required,)
    permission_required = ('manage_meeting',)

    def get(self):
        custom_field_id = request.args['id']
        cf = CustomField.query.get_or_404(custom_field_id)
        if cf.field_type == CustomField.CATEGORY:
            query = Category.get_categories_for_meeting(Category.PARTICIPANT)
            return jsonify(data=[(i.id, unicode(i)) for i in query])
        if cf.field_type == CustomField.COUNTRY:
            return jsonify(data=get_all_countries())
        return abort(400)
