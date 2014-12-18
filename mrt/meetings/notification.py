from flask import g, url_for, request, flash
from flask import render_template, redirect
from flask import jsonify
from flask.views import MethodView


from mrt.models import UserNotification, db
from mrt.forms.meetings import UserNotificationForm
from mrt.meetings.mixins import PermissionRequiredMixin


class Notifications(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', )

    def get(self):
        notifications = UserNotification.query.filter_by(meeting=g.meeting)
        return render_template('meetings/notification/list.html',
                               notifications=notifications)


class NotificationEdit(PermissionRequiredMixin, MethodView):

    permission_required = ('manage_meeting', )

    def get(self, notification_id=None):
        notification = (notification_id and
                        UserNotification.query.get_or_404(notification_id))
        form = UserNotificationForm(obj=notification)
        return render_template('meetings/notification/edit.html',
                               form=form,
                               notification=notification)

    def post(self, notification_id=None):
        notification = (notification_id and
                        UserNotification.query.get_or_404(notification_id))
        form = UserNotificationForm(request.form, obj=notification)
        if form.validate():
            form.save()
            if notification_id:
                flash('Notification successfully updated', 'success')
            else:
                flash('Notification successfully added', 'success')
            return redirect(url_for('.notifications'))
        flash('Notification was not saved. Plase see the errors bellow',
              'danger')
        return render_template('meetings/notification/edit.html',
                               form=form,
                               notification=notification)

    def delete(self, notification_id):
        notification = (notification_id and
                        UserNotification.query.get_or_404(notification_id))
        db.session.delete(notification)
        db.session.commit()
        flash('Notification successfully deleted', 'warning')
        return jsonify(status="success", url=url_for('.notifications'))
