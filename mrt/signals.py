from blinker import Namespace

_signals = Namespace()

activity_signal = _signals.signal('activity-signal')