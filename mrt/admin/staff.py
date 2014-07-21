from flask import render_template, request, redirect, url_for, jsonify
from flask.views import MethodView
from flask.ext.login import login_required

from mrt.models import db, Staff
from mrt.forms.admin import StaffEditForm


class StaffList(MethodView):
    decorators = (login_required, )

    def get(self):
        staff = Staff.query.all()
        return render_template('admin/staff/list.html', staff=staff)


class StaffEdit(MethodView):
    decorators = (login_required, )

    def get(self, staff_id=None):
        if staff_id:
            staff = Staff.query.get_or_404(staff_id)
            email = staff.user.email
        else:
            staff = None
            email = None
        form = StaffEditForm(obj=staff, email=email)

        return render_template('admin/staff/edit.html', form=form, staff=staff)

    def post(self, staff_id=None):
        if staff_id:
            staff = Staff.query.get_or_404(staff_id)
        else:
            staff = None
        form = StaffEditForm(request.form, obj=staff)
        if form.validate():
            form.save()
            return redirect(url_for('.staff'))

        return render_template('admin/staff/edit.html', form=form, staff=staff)

    def delete(self, staff_id):
        staff = Staff.query.get_or_404(staff_id)

        db.session.delete(staff)
        db.session.commit()
        response = {
            "status": "success",
            "url": url_for('.staff')
        }

        return jsonify(response).data
