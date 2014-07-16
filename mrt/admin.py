from flask import render_template, Blueprint, request, redirect, url_for
from flask.ext.login import login_required

from mrt.models import db, Staff
from mrt.forms.admin import StaffForm, StaffEditForm

admin = Blueprint("adin", __name__)


def initialize_app(app):
    app.register_blueprint(admin)


@admin.route('/admin/staff')
@login_required
def staff():
    staff = Staff.query.all()
    return render_template('admin/staff.html', staff=staff)


@admin.route('/admin/staff/add', methods=['GET', 'POST'])
@login_required
def staff_add():
    form = StaffForm(request.form)
    if request.method == 'POST' and form.validate():

        staff = Staff()
        form.populate_obj(staff)
        staff.user.set_password(staff.user.password)

        db.session.add(staff)
        db.session.commit()
        return redirect(url_for('.staff'))

    submit_url = url_for('.staff_add')

    return render_template('admin/add.html',
                           form=form,
                           submit_url=submit_url)


@admin.route('/admin/staff/<int:staff_id>/edit', methods=['GET', 'POST'])
@login_required
def staff_edit(staff_id=None):
    staff = Staff.query.get_or_404(staff_id)

    if request.method == 'GET':
        form = StaffEditForm(obj=staff)
    else:
        form = StaffEditForm(request.form)

        if form.validate():
            form.populate_obj(staff)
            db.session.add(staff)
            db.session.commit()
            return redirect(url_for('.staff'))

    submit_url = url_for('.staff_edit', staff_id=staff_id)
    return render_template('admin/add.html',
                           form=form,
                           staff_id=staff_id,
                           submit_url=submit_url)
