from flask import flash
from flask import render_template, jsonify
from flask import request, redirect, url_for
from flask.views import MethodView

from mrt.admin.mixins import PermissionRequiredMixin
from mrt.definitions import COLORS
from mrt.forms.admin import CategoryDefaultEditForm, CategoryClassEditForm
from mrt.models import db, CategoryDefault, CategoryClass, Category
from mrt.utils import unlink_uploaded_file


class Categories(PermissionRequiredMixin, MethodView):

    def get(self):
        categories = (
            CategoryDefault.query.order_by(CategoryDefault.sort)
            .order_by(CategoryDefault.id)
        )
        category_classes = (
            CategoryClass.query.order_by(CategoryClass.label)
        )

        return render_template('admin/category/list.html',
                               categories=categories,
                               category_classes=category_classes)


class CategoryEdit(PermissionRequiredMixin, MethodView):

    def get(self, category_id=None):
        category = (CategoryDefault.query.get_or_404(category_id)
                    if category_id else None)
        form = CategoryDefaultEditForm(obj=category)
        return render_template('admin/category/edit.html',
                               form=form,
                               category=category,
                               colors=COLORS)

    def post(self, category_id=None):
        category = (CategoryDefault.query.get_or_404(category_id)
                    if category_id else None)
        form = CategoryDefaultEditForm(request.form, obj=category)
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
                               form=form,
                               category=category,
                               colors=COLORS)

    def delete(self, category_id):
        category = CategoryDefault.query.get_or_404(category_id)
        db.session.delete(category)
        db.session.commit()
        unlink_uploaded_file(category.background, 'backgrounds')
        flash('Category successfully deleted', 'warning')
        return jsonify(status="success", url=url_for('.categories'))


class CategoryUpdatePosition(MethodView, PermissionRequiredMixin):

    def post(self):
        items = request.form.getlist('items[]')
        for i, item in enumerate(items):
            category = (
                CategoryDefault.query.filter_by(id=item)
                .first_or_404())
            category.sort = i
        db.session.commit()
        return jsonify()


class CategoryClassEdit(PermissionRequiredMixin, MethodView):

    def get(self, category_class_id=None):
        category_class = (CategoryClass.query.get_or_404(category_class_id)
                          if category_class_id else None)
        form = CategoryClassEditForm(obj=category_class)
        return render_template('admin/category_class/edit.html',
                               form=form,
                               category_class=category_class)

    def post(self, category_class_id=None):
        category_class = (CategoryClass.query.get_or_404(category_class_id)
                          if category_class_id else None)
        form = CategoryClassEditForm(request.form, obj=category_class)
        if form.validate():
            form.save()
            if category_class_id:
                flash('Category class successfully updated', 'success')
            else:
                flash('Category class successfully added', 'success')
            return redirect(url_for('.categories'))
        flash('Category class was not saved. Please see the errors bellow',
              'danger')
        return render_template('admin/category_class/edit.html',
                               form=form,
                               category_class=category_class)

    def delete(self, category_class_id):
        category_class = CategoryClass.query.get_or_404(category_class_id)

        categories_nr = (Category.query
                        .filter_by(category_class_id=category_class_id)
                        .count())
        categories_nr += (CategoryDefault.query
                          .filter_by(category_class_id=category_class_id)
                          .count())

        if categories_nr:
            categories_message = (
                'There is {} category' if categories_nr == 1
                else 'There are {} categories').format(categories_nr)
            message = 'Cannot delete {0}. {1} with this category class'.format(
                category_class.label, categories_message)
            return jsonify(status='error', message=message)

        db.session.delete(category_class)
        db.session.commit()
        flash('Category class successfully deleted', 'warning')
        return jsonify(status="success", url=url_for('.categories'))
