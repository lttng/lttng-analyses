# The MIT License (MIT)
#
# Copyright (C) 2015 - Julien Desfossez <jdesfossez@efficios.com>
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


class AnalysisConfig:
    def __init__(self):
        self.refresh_period = None
        self.period_begin_ev_name = None
        self.period_end_ev_name = None
        self.period_begin_key_fields = None
        self.period_end_key_fields = None
        self.period_key_value = None
        self.begin_ts = None
        self.end_ts = None
        self.min_duration = None
        self.max_duration = None
        self.proc_list = None
        self.tid_list = None
        self.cpu_list = None


class Analysis:
    TICK_CB = 'tick'

    def __init__(self, state, conf):
        self._state = state
        self._conf = conf
        self._period_key = None
        self._period_start_ts = None
        self._last_event_ts = None
        self._notification_cbs = {}
        self._cbs = {}

        self.started = False
        self.ended = False

    def process_event(self, ev):
        self._check_analysis_end(ev)
        if self.ended:
            return

        self._last_event_ts = ev.timestamp

        if not self.started:
            if self._conf.begin_ts:
                self._check_analysis_begin(ev)
                if not self.started:
                    return
            else:
                self._period_start_ts = ev.timestamp
                self.started = True

        # Prioritise period events over refresh period
        if self._conf.period_begin_ev_name is not None:
            self._handle_period_event(ev)
        elif self._conf.refresh_period is not None:
            self._check_refresh(ev)

    def reset(self):
        raise NotImplementedError()

    def end(self):
        if self._period_start_ts:
            self._end_period()

    def register_notification_cbs(self, cbs):
        for name in cbs:
            if name not in self._notification_cbs:
                self._notification_cbs[name] = []

            self._notification_cbs[name].append(cbs[name])

    def _send_notification_cb(self, name, **kwargs):
        if name in self._notification_cbs:
            for cb in self._notification_cbs[name]:
                cb(**kwargs)

    def _register_cbs(self, cbs):
        self._cbs = cbs

    def _process_event_cb(self, ev):
        name = ev.name

        if name in self._cbs:
            self._cbs[name](ev)
        elif 'syscall_entry' in self._cbs and \
             (name.startswith('sys_') or name.startswith('syscall_entry_')):
            self._cbs['syscall_entry'](ev)
        elif 'syscall_exit' in self._cbs and \
                (name.startswith('exit_syscall') or
                 name.startswith('syscall_exit_')):
            self._cbs['syscall_exit'](ev)

    def _check_analysis_begin(self, ev):
        if self._conf.begin_ts and ev.timestamp >= self._conf.begin_ts:
            self.started = True
            self._period_start_ts = ev.timestamp
            self.reset()

    def _check_analysis_end(self, ev):
        if self._conf.end_ts and ev.timestamp > self._conf.end_ts:
            self.ended = True

    def _check_refresh(self, ev):
        if not self._period_start_ts:
            self._period_start_ts = ev.timestamp
        elif ev.timestamp >= (self._period_start_ts +
                              self._conf.refresh_period):
            self._end_period()
            self._period_start_ts = ev.timestamp

    def _handle_period_event(self, ev):
        if ev.name != self._conf.period_begin_ev_name and \
           ev.name != self._conf.period_end_ev_name:
            return

        if self._period_key:
            period_key = Analysis._get_period_event_key(
                ev, self._conf.period_end_key_fields)

            if not period_key:
                # There was an error caused by a missing field, ignore
                # this period event
                return

            if period_key == self._period_key:
                if self._conf.period_end_ev_name:
                    if ev.name == self._conf.period_end_ev_name:
                        self._end_period()
                        self._period_key = None
                        self._period_start_ts = None
                elif ev.name == self._conf.period_begin_ev_name:
                    self._end_period()
                    self._begin_period(period_key, ev.timestamp)
        elif ev.name == self._conf.period_begin_ev_name:
            period_key = Analysis._get_period_event_key(
                ev, self._conf.period_begin_key_fields)

            if not period_key:
                return

            if self._conf.period_key_value:
                # Must convert the period key to string for comparison
                str_period_key = tuple(map(str, period_key))
                if self._conf.period_key_value != str_period_key:
                    return

            self._begin_period(period_key, ev.timestamp)

    def _begin_period(self, period_key, timestamp):
        self._period_key = period_key
        self._period_start_ts = timestamp
        self.reset()

    def _end_period(self):
        self._end_period_cb()
        self._send_notification_cb(Analysis.TICK_CB,
                                   begin_ns=self._period_start_ts,
                                   end_ns=self._last_event_ts)

    def _end_period_cb(self):
        pass

    @staticmethod
    def _get_period_event_key(ev, key_fields):
        if not key_fields:
            return None

        key_values = []

        for field in key_fields:
            try:
                key_values.append(ev[field])
            except KeyError:
                # Error: missing field
                return None

        return tuple(key_values)

    def _filter_process(self, proc):
        if not proc:
            return True
        if self._conf.proc_list and proc.comm not in self._conf.proc_list:
            return False
        if self._conf.tid_list and proc.tid not in self._conf.tid_list:
            return False
        return True

    def _filter_cpu(self, cpu):
        return not (self._conf.cpu_list and cpu not in self._conf.cpu_list)
