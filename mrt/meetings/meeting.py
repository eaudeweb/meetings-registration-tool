from flask import request, redirect, render_template, jsonify
from flask import g, url_for, flash
from flask.views import MethodView
from flask.ext.login import login_required

from sqlalchemy import desc

from mrt.models import Meeting, db
from mrt.forms import MeetingEditForm


class Meetings(MethodView):

    decorators = (login_required, )

    def get(self):
        meetings = Meeting.query.order_by(desc(Meeting.date_start))
        return render_template('meetings/meeting/list.html',
                               meetings=meetings)


class MeetingEdit(MethodView):

    decorators = (login_required, )

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
