from flask import g
from flask import render_template, flash
from flask import request, redirect, url_for, jsonify
from flask.ext.login import login_required
from flask.views import MethodView

from mrt.forms.meetings import MeetingCategoryAddForm
from mrt.forms.admin import CategoryEditForm
from mrt.models import db, Category
from mrt.utils import unlink_uploaded_file
from mrt.definitions import COLORS


class Categories(MethodView):

    decorators = (login_required,)

    def get(self):
        categories = (Category.query.filter(Category.meeting == g.meeting)
                      .order_by(Category.sort)
                      .order_by(Category.id))
        form = MeetingCategoryAddForm()
        return render_template('meetings/category/list.html',
                               categories=categories,
                               form=form)

    def post(self):
        categories = (Category.query.filter(Category.meeting == g.meeting)
                      .order_by(Category.sort))
        form = MeetingCategoryAddForm(request.form)
        if form.validate():
            form.save()
            return redirect(url_for('.categories'))
        return render_template('meetings/category/list.html',
                               categories=categories,
                               form=form)


class CategoryEdit(MethodView):

    decorators = (login_required,)

    def get(self, category_id):
        category = Category.query.filter_by(
            id=category_id,
            meeting_id=g.meeting.id).first_or_404()
        form = CategoryEditForm(obj=category)
        return render_template('meetings/category/edit.html',
                               category=category,
                               form=form,
                               colors=COLORS)

    def post(self, category_id):
        category = Category.query.filter_by(
            id=category_id,
            meeting_id=g.meeting.id).first_or_404()
        form = CategoryEditForm(request.form, obj=category)
        if form.validate():
            form.save()
            flash('Category successfully updated', 'success')
            return redirect(url_for('.categories'))
        flash('Category was not saved. Please see the errors bellow',
              'danger')
        return render_template('meetings/category/edit.html',
                               form=form,
                               category=category,
                               colors=COLORS)

    def delete(self, category_id):
        category = Category.query.filter_by(
            id=category_id,
            meeting_id=g.meeting.id).first_or_404()
        db.session.delete(category)
        db.session.commit()
        unlink_uploaded_file(category.background, 'backgrounds')
        flash('Category successfully deleted', 'warning')
        return jsonify(status="success", url=url_for('.categories'))
