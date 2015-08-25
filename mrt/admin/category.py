from flask import flash
from flask import render_template, jsonify
from flask import request, redirect, url_for
from flask.views import MethodView

from mrt.admin.mixins import PermissionRequiredMixin
from mrt.definitions import COLORS
from mrt.forms.admin import CategoryDefaultEditForm, CategoryTagEditForm
from mrt.models import db, CategoryDefault, CategoryTag, Category
from mrt.utils import unlink_uploaded_file


class Categories(PermissionRequiredMixin, MethodView):

    def get(self):
        categories = (
            CategoryDefault.query.order_by(CategoryDefault.sort)
            .order_by(CategoryDefault.id)
        )
        category_tags = (
            CategoryTag.query.order_by(CategoryTag.label)
        )

        return render_template('admin/category/list.html',
                               categories=categories,
                               category_tags=category_tags)


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


class CategoryTagEdit(PermissionRequiredMixin, MethodView):

    def get(self, category_tag_id=None):
        category_tag = (CategoryTag.query.get_or_404(category_tag_id)
                          if category_tag_id else None)
        form = CategoryTagEditForm(obj=category_tag)
        return render_template('admin/category_tag/edit.html',
                               form=form,
                               category_tag=category_tag)

    def post(self, category_tag_id=None):
        category_tag = (CategoryTag.query.get_or_404(category_tag_id)
                          if category_tag_id else None)
        form = CategoryTagEditForm(request.form, obj=category_tag)
        if form.validate():
            form.save()
            if category_tag_id:
                flash('Category tag successfully updated', 'success')
            else:
                flash('Category tag successfully added', 'success')
            return redirect(url_for('.categories'))
        flash('Category tag was not saved. Please see the errors bellow',
              'danger')
        return render_template('admin/category_tag/edit.html',
                               form=form,
                               category_tag=category_tag)

    def delete(self, category_tag_id):
        category_tag = CategoryTag.query.get_or_404(category_tag_id)

        categories_nr = category_tag.default_categories.count()
        categories_nr += category_tag.categories.count()

        if categories_nr:
            categories_message = (
                'There is {} category' if categories_nr == 1
                else 'There are {} categories').format(categories_nr)
            message = 'Cannot delete {0}. {1} with this category tag'.format(
                category_tag.label, categories_message)
            return jsonify(status='error', message=message)

        db.session.delete(category_tag)
        db.session.commit()
        flash('Category tag successfully deleted', 'warning')
        return jsonify(status="success", url=url_for('.categories'))
