from flask import (
    render_template, request, redirect, url_for, flash, jsonify, abort)
from flask.views import MethodView
from flask.ext.login import login_required

from mrt.admin.mixins import PermissionRequiredMixin
from mrt.models import MeetingType, db
from mrt.forms.admin import MeetingTypeEditForm


class MeetingTypes(PermissionRequiredMixin, MethodView):

    decorators = (login_required,)

    def get(self):
        meeting_types = MeetingType.query.ignore_def()
        return render_template('admin/meeting_type/list.html',
                               meeting_types=meeting_types)


class MeetingTypeEdit(PermissionRequiredMixin, MethodView):

    decorators = (login_required,)

    def get(self, meeting_type_slug=None):
        meeting_type = (
            MeetingType.query.get_or_404(meeting_type_slug)
            if meeting_type_slug else None
        )
        form = MeetingTypeEditForm(obj=meeting_type)
        return render_template('admin/meeting_type/edit.html',
                               form=form,
                               meeting_type=meeting_type)

    def post(self, meeting_type_slug=None):
        meeting_type = (
            MeetingType.query.get_or_404(meeting_type_slug)
            if meeting_type_slug else None)

        form = MeetingTypeEditForm(request.form, obj=meeting_type)
        if form.validate():
            form.save()
            if meeting_type_slug:
                flash('Meeting type successfully updated', 'success')
            else:
                flash('Meeting type successfully added', 'success')
            return redirect(url_for('.meeting_types'))

        flash('Meeting type was not saved. Please see the errors bellow',
              'danger')
        return render_template('admin/meeting_type/edit.html',
                               form=form,
                               meeting_type=meeting_type)

    def delete(self, meeting_type_slug):
        meeting_type = MeetingType.query.get_or_404(meeting_type_slug)
        if meeting_type.default:
            abort(403)

        meetings_nr = meeting_type.meetings.count()
        if meetings_nr:
            meetings_message = (
                'There is {} meeting' if meetings_nr == 1
                else 'There are {} meetings').format(meetings_nr)
            message = 'Cannot delete {0}. {1} with this meeting type'.format(
                meeting_type.label, meetings_message)
            return jsonify(status='error', message=message)

        db.session.delete(meeting_type)
        db.session.commit()
        flash('Meeting type successfully deleted', 'warning')
        return jsonify(status="success", url=url_for('.meeting_types'))
