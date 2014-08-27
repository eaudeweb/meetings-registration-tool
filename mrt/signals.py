from blinker import Namespace

_signals = Namespace()

activity_signal = _signals.signal('activity-signal')
notification_signal = _signals.signal('notification-signal')
