from .analysis import Analysis


class Memtop(Analysis):
    def __init__(self, state):
        self._state = state

    def process_event(self, ev):
        pass
