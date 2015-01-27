from .net import NetStateProvider


class State:
    def __init__(self):
        self.hello = 23

    def _incr_hello(self):
        self.hello += 5


class Automaton:
    def __init__(self):
        self._state = State()
        self._state_providers = [
            NetStateProvider(self._state),
        ]

    def process_event(self, ev):
        for sp in self._state_providers:
            sp.process_event(ev)

    @property
    def state(self):
        return self._state
