from flask.views import MethodView
from flask import g, render_template, jsonify, abort, request
from mrt.forms.meetings import RuleForm
from mrt.models import Category, CustomField
from mrt.utils import get_all_countries


class Rules(MethodView):

    def get(self):
        pass


class RuleEdit(MethodView):

    def get(self):
        form = RuleForm()
        return render_template('meetings/rule/edit.html', form=form)

    def post(self):
        pass


class RulesData(MethodView):

    def get(self):
        custom_field_id = request.args['id']
        cf = CustomField.query.get_or_404(custom_field_id)
        if cf.field_type == CustomField.CATEGORY:
            query = (Category.query.filter_by(meeting=g.meeting)
                     .filter_by(category_type=Category.PARTICIPANT)
                     .order_by(Category.group, Category.sort))
            return jsonify(data=[(i.id, unicode(i)) for i in query])
        if cf.field_type == CustomField.COUNTRY:
            return jsonify(data=get_all_countries())
        return abort(400)
