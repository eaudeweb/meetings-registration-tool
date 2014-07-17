from flask import render_template, request, redirect, url_for, jsonify
from flask.views import MethodView
from flask.ext.login import login_required

from mrt.models import db, Staff
from mrt.forms.admin import StaffAddForm, StaffEditForm


class StaffList(MethodView):
    decorators = (login_required, )

    def get(self):
        staff = Staff.query.all()
        return render_template('admin/staff.html', staff=staff)


class StaffEdit(MethodView):
    decorators = (login_required, )

    def get(self, staff_id=None):
        if staff_id:
            staff = Staff.query.get_or_404(staff_id)
            form = StaffEditForm(obj=staff)
        else:
            staff = None
            form = StaffAddForm()

        return render_template('admin/edit.html', form=form, staff=staff)

    def post(self, staff_id=None):
        if staff_id:
            staff = Staff.query.get_or_404(staff_id)
            form = StaffEditForm(request.form, obj=staff)
        else:
            staff = None
            form = StaffAddForm(request.form)

        if form.validate():
            form.save()
            return redirect(url_for('.list'))

        return render_template('admin/edit.html', form=form, staff=staff)

    def delete(self, staff_id):
        staff = Staff.query.get_or_404(staff_id)

        db.session.delete(staff)
        db.session.commit()
        response = {
            "status": "success",
            "url": url_for('.list')
        }

        return jsonify(response).data
