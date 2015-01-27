from .analysis import Analysis


class Cputop(Analysis):
    def __init__(self, state):
        self._state = state
        self._ev_count = 0

    def process_event(self, ev):
        self._ev_count += 1

    @property
    def event_count(self):
        return self._ev_count
