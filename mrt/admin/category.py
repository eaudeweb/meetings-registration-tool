from flask import flash
from flask import render_template, jsonify
from flask import request, redirect, url_for
from flask.views import MethodView
from flask.ext.login import login_required

from mrt.forms.admin import CategoryEditForm
from mrt.models import db, CategoryDefault
from mrt.utils import unlink_uploaded_file


class Categories(MethodView):

    decorators = (login_required,)

    def get(self):
        categories = CategoryDefault.query.order_by(CategoryDefault.sort)
        return render_template('admin/category/list.html',
                               categories=categories)


class CategoryEdit(MethodView):

    decorators = (login_required, )

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
            if category_id:
                flash('Category successfully updated', 'success')
            else:
                flash('Category successfully added', 'success')
            return redirect(url_for('.categories'))
        flash('Category was not saved. Please see the errors bellow',
              'danger')
        return render_template('admin/category/edit.html',
                               form=form, category=category)

    def delete(self, category_id):
        category = CategoryDefault.query.get_or_404(category_id)
        db.session.delete(category)
        db.session.commit()
        unlink_uploaded_file(category.background, 'backgrounds')
        flash('Category successfully deleted', 'warning')
        return jsonify(status="success", url=url_for('.categories'))
