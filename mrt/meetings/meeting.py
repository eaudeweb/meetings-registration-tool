from functools import wraps

from flask import request, redirect, render_template, jsonify
from flask import g, url_for, flash
from flask.views import MethodView
from flask.ext.login import login_required, current_user as user

from sqlalchemy import desc

from mrt.models import Meeting, db, RoleUser, MeetingType
from mrt.forms.meetings import MeetingEditForm, MeetingFilterForm
from mrt.meetings.mixins import PermissionRequiredMixin


def _check_meeting_type():
    if MeetingType.query.ignore_def().count() == 0:
        return render_template('meetings/meeting_type_required.html')


def _meeting_type_required(func):
    @wraps(func)
    def wrapper(**kwargs):
        return _check_meeting_type() or func(**kwargs)
    return wrapper


class MeetingsPermissionRequiredMixin(PermissionRequiredMixin):

    def check_permissions(self):
        if (user.is_superuser or RoleUser.query.filter_by(user=user).first()):
            return True
        return False


class Meetings(MeetingsPermissionRequiredMixin, MethodView):

    decorators = (login_required,)

    def get(self):
        qs = Meeting.query.ignore_def().order_by(desc(Meeting.date_start))
        if not user.is_superuser:
            qs = qs.outerjoin(RoleUser).filter((RoleUser.user == user) |
                                               (Meeting.owner == user.staff))

        meeting_type = request.args.get('meeting_type', None)
        if meeting_type:
            qs = qs.filter(Meeting.meeting_type.has(slug=meeting_type))

        filter_form = MeetingFilterForm(request.args)
        return render_template('meetings/meeting/list.html',
                               meetings=qs, filter_form=filter_form)


class MeetingEdit(PermissionRequiredMixin, MethodView):

    decorators = (login_required, _meeting_type_required)
    permission_required = ('manage_meeting',)

    def get(self):
        form = MeetingEditForm(obj=g.meeting)
        return render_template('meetings/meeting/edit.html',
                               form=form)

    def post(self):
        form = MeetingEditForm(request.form, obj=g.meeting)
        if form.validate():
            meeting = form.save()
            if g.meeting:
                flash('Meeting successfully updated', 'success')
            else:
                flash('Meeting successfully added', 'success')
            return redirect(url_for('.participants', meeting_id=meeting.id))
        flash('Meeting was not saved. Please see the errors bellow', 'danger')
        return render_template('meetings/meeting/edit.html', form=form)

    def delete(self):
        db.session.delete(g.meeting)
        db.session.commit()
        flash('Meeting successfully deleted', 'warning')
        return jsonify(status="success", url=url_for('.home'))
