from collections import namedtuple

from werkzeug.datastructures import MultiDict

from flask import g, render_template, jsonify, abort, request
from flask import redirect, url_for, flash
from flask.ext.login import login_required
from flask.views import MethodView

from mrt.forms.meetings import RuleForm, ConditionForm
from mrt.meetings.mixins import PermissionRequiredMixin
from mrt.models import Category, CustomField, Rule
from mrt.models import db
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

    def get_object(self, rule_id):
        return (Rule.query.filter_by(id=rule_id, meeting=g.meeting)
                .first_or_404() if rule_id else None)

    def process_formdata(self, rule):
        Condition = namedtuple('Condition', ['field', 'values'])
        Action = namedtuple('Action', ['field', 'is_required', 'is_visible'])
        conditions, actions = [], []
        for condition in rule.conditions.all():
            values = [i.value for i in condition.values.all()]
            conditions.append(Condition(condition.field.id, values))
        for action in rule.actions.all():
            actions.append(Action(action.field.id, action.is_required,
                                  action.is_visible))
        return MultiDict({'conditions': conditions, 'actions': actions})

    def get(self, rule_id=None):
        rule = self.get_object(rule_id)
        data = self.process_formdata(rule) if rule else None
        form = RuleForm(data=data, rule=rule)
        return render_template('meetings/rule/edit.html',
                               form=form, rule=rule)

    def post(self, rule_id=None):
        rule = self.get_object(rule_id)
        data = self.process_formdata(rule) if rule else None
        form = RuleForm(request.form, data=data, rule=rule)
        if form.validate():
            form.save()
            return redirect(url_for('.rules'))
        return render_template('meetings/rule/edit.html',
                               form=form, rule=rule)

    def delete(self, rule_id):
        rule = self.get_object(rule_id)
        db.session.delete(rule)
        db.session.commit()
        flash('Rule successfully deleted', 'warning')
        return jsonify(status='success', url=url_for('.rules'))


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
        if cf.field_type == CustomField.CHECKBOX:
            return jsonify(data=ConditionForm.CHECKBOX_VALUES)
        return abort(400)
