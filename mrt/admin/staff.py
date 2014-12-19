from flask import render_template, flash
from flask import request, redirect, url_for, jsonify
from flask.ext.login import login_required
from flask.views import MethodView

from mrt.admin.mixins import PermissionRequiredMixin
from mrt.forms.admin import StaffEditForm
from mrt.models import db, Staff, RoleUser


class StaffList(PermissionRequiredMixin, MethodView):

    decorators = (login_required, )

    def get(self):
        staff = Staff.query.order_by(Staff.id)
        return render_template('admin/staff/list.html', staff=staff)


class StaffEdit(PermissionRequiredMixin, MethodView):

    decorators = (login_required, )

    def get(self, staff_id=None):
        if staff_id:
            staff = Staff.query.get_or_404(staff_id)
        else:
            staff = None
        form = StaffEditForm(obj=staff)
        return render_template('admin/staff/edit.html', form=form, staff=staff)

    def post(self, staff_id=None):
        if staff_id:
            staff = Staff.query.get_or_404(staff_id)
        else:
            staff = None
        form = StaffEditForm(request.form, obj=staff)
        if form.validate():
            form.save()
            if staff_id:
                flash('Staff successfully updated', 'success')
            else:
                flash('Staff successfully added', 'success')
            return redirect(url_for('.staff'))
        flash('Staff was not saved. Please see the errors bellow',
              'danger')
        return render_template('admin/staff/edit.html', form=form, staff=staff)

    def delete(self, staff_id):
        staff = Staff.query.get_or_404(staff_id)
        role_user = RoleUser.query.filter_by(user=staff.user,
                                             meeting=None).one()
        db.session.delete(staff)
        db.session.delete(role_user)
        db.session.commit()
        flash('Staff successfully deleted', 'warning')
        return jsonify(status="success", url=url_for('.staff'))
