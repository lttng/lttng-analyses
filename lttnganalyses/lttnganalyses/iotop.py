from .analysis import Analysis


class Iotop(Analysis):
    def __init__(self, state, split, split_count):
        self._state = state
        self._split = split
        self._split_count = split_count
        self._ev_count = 0
        self._tmp_ev_count = 0
        self._buckets = []
        self._last_reset_hello = state.hello

        if not self._split:
            self._buckets.append(0)

    def process_event(self, ev):
        self._ev_count += 1
        self._tmp_ev_count += 1

        if self._split:
            if self._tmp_ev_count == self._split_count:
                self._tmp_ev_count = 0
                cur_hello_diff = self._state.hello - self._last_reset_hello
                self._last_reset_hello = self._state.hello
                self._buckets.append(cur_hello_diff)
        else:
            self._buckets[0] = self._state.hello

    @property
    def buckets(self):
        return self._buckets

    @property
    def event_count(self):
        return self._ev_count
