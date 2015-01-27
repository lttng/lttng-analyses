from .net import NetStateProvider
from .sched import SchedStateProvider


class State:
    def __init__(self):
        self.cpus = {}
        self.tids = {}
        self.dirty_pages = {}


class Automaton:
    def __init__(self):
        self._state = State()
        self._state_providers = [
            NetStateProvider(self._state),
            SchedStateProvider(self._state),
        ]

    def process_event(self, ev):
        for sp in self._state_providers:
            sp.process_event(ev)

    @property
    def state(self):
        return self._state
