from flask import g
from flask import render_template
from flask import request, redirect, url_for
from flask.ext.login import login_required
from flask.views import MethodView

from mrt.forms.meetings import MeetingCategoryAddForm
from mrt.models import Category


class Categories(MethodView):

    decorators = (login_required,)

    def get(self):
        categories = (Category.query.filter(Category.meeting == g.meeting)
                      .order_by(Category.sort))
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

    def get(self):
        return render_template('meetings/category/edit.html')
