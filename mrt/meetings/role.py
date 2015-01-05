from flask import g, request, redirect, jsonify
from flask import render_template, url_for, flash
from flask.ext.login import login_required
from flask.views import MethodView

from mrt.models import db, RoleUser
from mrt.forms.meetings import RoleUserEditForm, MeetingChangeOwnerForm
from mrt.meetings.mixins import PermissionRequiredMixin


class Roles(PermissionRequiredMixin, MethodView):

    decorators = (login_required,)
    permission_required = ('manage_meeting',)

    def get(self):
        role_users = RoleUser.query.filter(RoleUser.meeting == g.meeting)
        return render_template('meetings/role/list.html',
                               role_users=role_users)


class RoleUserEdit(PermissionRequiredMixin, MethodView):

    decorators = (login_required,)
    permission_required = ('manage_meeting',)

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
        return render_template('meetings/role/edit.html',
                               form=form,
                               role_user=role_user)

    def delete(self, role_user_id):
        role_user = RoleUser.query.get_or_404(role_user_id)
        db.session.delete(role_user)
        db.session.commit()
        flash('Role User successfully deleted', 'warning')
        return jsonify(status="success", url=url_for('.roles'))


class RoleMeetingChangeOwner(PermissionRequiredMixin, MethodView):

    decorators = (login_required,)
    permission_required = ('manage_meeting',)

    def get(self):
        form = MeetingChangeOwnerForm(obj=g.meeting)
        return render_template('meetings/role/change_owner.html',
                               form=form)

    def post(self):
        form = MeetingChangeOwnerForm(request.form, obj=g.meeting)
        if form.validate():
            form.save()
            flash('Meeting owner changed to %s' % g.meeting.owner,
                  'success')
            return jsonify(status='success', url=url_for('.roles'))
        html = render_template('meetings/role/change_owner.html',
                               form=form)
        return jsonify(status='error', html=html)
