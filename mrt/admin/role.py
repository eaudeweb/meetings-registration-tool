from flask import request, redirect, url_for, jsonify
from flask import render_template, flash
from flask.views import MethodView
from flask.ext.login import login_required

from mrt.models import db, Role, RoleUser
from mrt.forms.admin import RoleEditForm


class Roles(MethodView):

    decorators = (login_required,)

    def get(self):
        roles = Role.query.all()
        return render_template('admin/role/list.html', roles=roles)


class RoleEdit(MethodView):

    decorators = (login_required,)

    def get(self, role_id=None):
        role = role_id and Role.query.get_or_404(role_id)
        form = RoleEditForm(obj=role)
        return render_template('admin/role/edit.html', form=form, role=role)

    def post(self, role_id=None):
        role = role_id and Role.query.get_or_404(role_id)
        form = RoleEditForm(request.form, obj=role)
        if form.validate():
            form.save()
            if role_id:
                flash('Role successfully updated', 'success')
            else:
                flash('Role successfully added', 'success')
            return redirect(url_for('.roles'))
        flash('Role was not saved. Plase see the errors bellow', 'danger')
        return render_template('admin/role/edit.html', form=form, role=role)

    def delete(self, role_id):
        role = Role.query.get_or_404(role_id)
        if RoleUser.query.filter_by(role=role).first():
            return jsonify(status="error",
                           message="There are staff members with this role")
        db.session.delete(role)
        db.session.commit()
        flash('Role successfully deleted', 'warning')
        return jsonify(status="success", url=url_for('.roles'))
