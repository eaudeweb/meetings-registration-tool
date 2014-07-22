from flask import request, redirect, url_for
from flask import render_template, jsonify
from flask.views import MethodView

from mrt.models import db, CategoryDefault
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
        return render_template('admin/category/edit.html',
                               form=form, category=category)

    def post(self, category_id=None):
        if category_id:
            category = CategoryDefault.query.get_or_404(category_id)
        else:
            category = None
        form = CategoryEditForm(request.form, obj=category)
        if form.validate():
            form.save()
            return redirect(url_for('.categories'))
        return render_template('admin/category/edit.html',
                               form=form, category=category)

    def delete(self, category_id):
        category = CategoryDefault.query.get_or_404(category_id)
        db.session.delete(category)
        db.session.commit()
        return jsonify(status="success", url=url_for('.categories'))
