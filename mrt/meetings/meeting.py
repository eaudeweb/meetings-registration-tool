from flask import request, redirect, render_template, jsonify
from flask import g, url_for, flash, abort
from flask.views import MethodView
from flask.ext.login import login_required, current_user

from sqlalchemy import desc

from mrt.models import Meeting, db
from mrt.forms.meetings import MeetingEditForm


class PermissionRequiredMixin(object):

    permission_required = None

    def get_permission_required(self):
        if self.permission_required is None:
            #raise exception
            abort(403)
        return self.permission_required

    def check_permissions(self):
        perms = self.get_permission_required()
        return current_user.has_perms(perms)

    def dispatch_request(self, *args, **kwargs):
        if not self.check_permissions():
            abort(403)
        return super(PermissionRequiredMixin, self).dispatch_request(
            *args, **kwargs)


class Meetings(MethodView):

    decorators = (login_required, )

    def get(self):
        meetings = Meeting.query.order_by(desc(Meeting.date_start))
        return render_template('meetings/meeting/list.html',
                               meetings=meetings)


class MeetingEdit(PermissionRequiredMixin, MethodView):

    decorators = (login_required, )
    permission_required = ('add_meeting', 'delete_meeting', 'edit_meeting')

    def get(self):
        form = MeetingEditForm(obj=g.meeting)
        return render_template('meetings/meeting/edit.html',
                               form=form)

    def post(self):
        form = MeetingEditForm(request.form, obj=g.meeting)
        if form.validate():
            form.save()
            if g.meeting:
                flash('Meeting successfully updated', 'success')
            else:
                flash('Meeting successfully added', 'success')
            return redirect(url_for('.home'))
        flash('Meeting was not saved. Please see the errors bellow', 'danger')
        return render_template('meetings/meeting/edit.html', form=form)

    def delete(self):
        db.session.delete(g.meeting)
        db.session.commit()
        flash('Meeting successfully deleted', 'warning')
        return jsonify(status="success", url=url_for('.home'))
