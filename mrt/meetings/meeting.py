from functools import wraps

from flask import request, redirect, render_template, jsonify
from flask import g, url_for, flash, make_response
from flask.views import MethodView
from flask.ext.login import login_required, current_user as user

from sqlalchemy import desc

from mrt.models import Meeting, db, RoleUser, MeetingType
from mrt.forms.meetings import MeetingEditForm, MeetingCloneForm
from mrt.forms.meetings import MeetingFilterForm, MeetingLogoEditForm
from mrt.meetings.mixins import PermissionRequiredMixin
from mrt.utils import unlink_meeting_logo, get_meeting_logo


def _check_meeting_type():
    if MeetingType.query.ignore_def().count() == 0:
        return render_template('meetings/meeting_type_required.html')


def _meeting_type_required(func):
    @wraps(func)
    def wrapper(**kwargs):
        return _check_meeting_type() or func(**kwargs)
    return wrapper


class Meetings(MethodView):

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


class MeetingBase(PermissionRequiredMixin, MethodView):

    decorators = (login_required, _meeting_type_required)
    permission_required = ('manage_meeting',)

    def get(self):
        form = self.form_class(obj=g.meeting)
        return render_template('meetings/meeting/edit.html', form=form,
                               **self.template_vars)

    def post(self):
        form = self.form_class(request.form, obj=g.meeting)
        if form.validate():
            meeting = form.save()
            flash(self.success_message, 'success')
            return redirect(url_for('.participants', meeting_id=meeting.id))
        flash('Meeting was not saved. Please see the errors bellow', 'danger')
        return render_template('meetings/meeting/edit.html', form=form,
                               **self.template_vars)

    def delete(self):
        db.session.delete(g.meeting)
        db.session.commit()
        flash('Meeting successfully deleted', 'warning')
        return jsonify(status="success", url=url_for('.home'))


class MeetingAdd(MeetingBase):
    form_class = MeetingEditForm
    success_message = 'Meeting successfully added'
    template_vars = {'title': 'Add a new meeting', 'can_delete': False}


class MeetingEdit(MeetingBase):
    form_class = MeetingEditForm
    success_message = 'Meeting successfully updated'
    template_vars = {'title': 'Edit meeting', 'can_delete': True}


class MeetingClone(MeetingBase):
    form_class = MeetingCloneForm
    success_message = 'Meeting successfully added'
    template_vars = {'title': 'Clone meeting', 'can_delete': False}


class MeetingLogoUpload(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting',)

    def post(self, logo_slug):
        form = MeetingLogoEditForm(request.files)
        if form.validate():
            data = form.save(logo_slug)
        else:
            return make_response(jsonify(form.errors), 400)

        html = render_template('meetings/overview/_image_container.html',
                               data=data)
        return jsonify(html=html)

    def delete(self, logo_slug):
        old_logo = get_meeting_logo(logo_slug)
        unlink_meeting_logo(old_logo)
        return jsonify(status="success", url=url_for('.statistics'))
