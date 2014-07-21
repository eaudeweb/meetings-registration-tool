from flask import render_template
from flask.views import MethodView
from mrt.models import CategoryDefault


class Categories(MethodView):

    def get(self):
        categories = CategoryDefault.query.all()
        return render_template('admin/category/list.html',
                               categories=categories)
