# The MIT License (MIT)
#
# Copyright (C) 2016 - Julien Desfossez <jdesfossez@efficios.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from .analysis import Analysis, PeriodData


class _PeriodData(PeriodData):
    pass


class PeriodAnalysis(Analysis):
    def __init__(self, state, conf):
        super().__init__(state, conf, {})
        # This is a special case where we keep a global state instead of a
        # per-period state, since we are accumulating statistics about
        # all the periods.
        self._all_period_stats = {}
        self._all_period_list = []
        self._all_total_duration = 0
        self._all_min_duration = None
        self._all_max_duration = None

    def _create_period_data(self):
        return _PeriodData()

    @property
    def all_count(self):
        return len(self._all_period_list)

    @property
    def all_period_stats(self):
        return self._all_period_stats

    @property
    def all_period_list(self):
        return self._all_period_list

    @property
    def all_min_duration(self):
        return self._all_min_duration

    @property
    def all_max_duration(self):
        return self._all_max_duration

    @property
    def all_total_duration(self):
        return self._all_total_duration

    def update_global_stats(self, period_event):
        if self._all_min_duration is None or period_event.duration < \
                self._all_min_duration:
            self._all_min_duration = period_event.duration

        if self._all_max_duration is None or period_event.duration > \
                self._all_max_duration:
            self._all_max_duration = period_event.duration
        self._all_total_duration += period_event.duration
        self._all_period_list.append(period_event)

    # beginning of a new period
    def _begin_period_cb(self, period_data):
        if period_data.period.definition is None:
            return

        definition = period_data.period.definition

        if definition.name not in self._all_period_stats:
            self._all_period_stats[definition.name] = \
                PeriodStats.new_from_period(period_data.period)

    def _end_period_cb(self, period_data, completed,
                       begin_captures, end_captures):
        period = period_data.period

        if period.definition is None:
            return

        if completed is False:
            return

        new_period_evt = PeriodEvent(period.begin_evt.timestamp,
                                     self.last_event_ts,
                                     period.definition.name,
                                     begin_captures,
                                     end_captures)
        self._all_period_stats[period.definition.name].update_stats(
            new_period_evt)
        self.update_global_stats(new_period_evt)


class PeriodStats():
    def __init__(self, name):
        self.name = name
        self.period_list = []
        self.min_duration = None
        self.max_duration = None
        self.total_duration = 0

    @classmethod
    def new_from_period(cls, period):
        return cls(period.definition.name)

    @property
    def count(self):
        return len(self.period_list)

    def update_stats(self, period_event):
        if self.min_duration is None or period_event.duration < \
                self.min_duration:
            self.min_duration = period_event.duration

        if self.max_duration is None or period_event.duration > \
                self.max_duration:
            self.max_duration = period_event.duration
        self.total_duration += period_event.duration
        self.period_list.append(period_event)


class PeriodEvent():
    def __init__(self, start_ts, end_ts, name, begin_captures,
                 end_captures):
        self._start_ts = start_ts
        self._end_ts = end_ts
        self._name = name
        self._begin_captures = begin_captures
        self._end_captures = end_captures

    @property
    def start_ts(self):
        return self._start_ts

    @property
    def end_ts(self):
        return self._end_ts

    @property
    def name(self):
        return self._name

    @property
    def duration(self):
        return self._end_ts - self._start_ts
