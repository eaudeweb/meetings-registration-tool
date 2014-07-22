from flask import request, redirect, url_for
from flask import render_template
from flask.views import MethodView

from mrt.models import CategoryDefault
from mrt.forms import CategoryEditForm


class Categories(MethodView):

    def get(self):
        categories = CategoryDefault.query.all()
        return render_template('admin/category/list.html',
                               categories=categories)


class CategoryEdit(MethodView):

    def get(self, category_id=None):
        if category_id:
            category = CategoryDefault.query.get_or_404(category_id)
        else:
            category = None
        form = CategoryEditForm(obj=category)
        return render_template('admin/category/edit.html', form=form)

    def post(self, category_id=None):
        if category_id:
            category = CategoryDefault.query.get_or_404(category_id)
        else:
            category = None
        form = CategoryEditForm(request.form, obj=category)
        print form.validate(), form.errors
        if form.validate():
            form.save()
            return redirect(url_for('.categories'))
        return render_template('admin/category/edit.html', form=form)
