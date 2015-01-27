class StateProvider:
    def process_event(self, ev):
        raise NotImplementedError()

    def _register_cbs(self, cbs):
        self._cbs = cbs

    def _process_event_cb(self, ev):
        name = ev.name

        if name in self._cbs:
            self._cbs[name](ev)
