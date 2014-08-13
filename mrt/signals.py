from flask.ext.login import current_user as user

from blinker import Namespace, ANY
from datetime import datetime

from mrt.models import db, ActivityLog, Staff

_signals = Namespace()

activity_signal = _signals.signal('activity-signal')


@activity_signal.connect_via(ANY)
def activity_listener(sender, participant, action):
    staff = Staff.query.filter_by(user=user).first()
    activity = ActivityLog(participant=participant, staff=staff,
                           action=action, date=datetime.now())
    db.session.add(activity)
    db.session.commit()
