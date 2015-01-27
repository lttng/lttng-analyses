from linuxautomaton import sp


class NetStateProvider(sp.StateProvider):
    def __init__(self, state):
        self._state = state
        cbs = {
            'hello': self._process_hello_event,
        }

        self._register_cbs(cbs)

    def process_event(self, ev):
        self._process_event_cb(ev)

    def _process_hello_event(self, ev):
        if ev.cond:
            self._state._incr_hello()
