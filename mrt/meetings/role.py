from flask import g, request, redirect
from flask import render_template, url_for, flash
from flask.ext.login import login_required
from flask.views import MethodView

from mrt.models import RoleUser
from mrt.forms.meetings import RoleUserEditForm


class Roles(MethodView):

    decorators = (login_required,)

    def get(self):
        role_users = RoleUser.query.filter(RoleUser.meeting == g.meeting)
        return render_template('meetings/role/list.html',
                               role_users=role_users)


class RoleUserEdit(MethodView):

    decorators = (login_required,)

    def get(self, role_user_id=None):
        role_user = role_user_id and RoleUser.query.get_or_404(role_user_id)
        form = RoleUserEditForm(obj=role_user)
        return render_template('meetings/role/edit.html',
                               role_user=role_user,
                               form=form)

    def post(self, role_user_id=None):
        role_user = role_user_id and RoleUser.query.get_or_404(role_user_id)
        form = RoleUserEditForm(request.form, obj=role_user)
        if form.validate():
            form.save()
            if role_user_id:
                flash('RoleUser successfully updated', 'success')
            else:
                flash('RoleUser successfully added', 'success')
            return redirect(url_for('.roles'))
        flash('RoleUser was not saved. Plase see the errors bellow', 'danger')
        return render_template('admin/role/edit.html',
                               form=form,
                               role_user=role_user)
