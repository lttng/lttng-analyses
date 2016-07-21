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

from . import period as core_period
import enum


class AnalysisConfig:
    def __init__(self):
        self.refresh_period = None
        self.begin_ts = None
        self.end_ts = None
        self.min_duration = None
        self.max_duration = None
        self.proc_list = None
        self.tid_list = None
        self.cpu_list = None
        self.period_def_registry = core_period.PeriodDefinitionRegistry()


# base class for all specific period data classes in specific analyses
class PeriodData:
    def _set_period(self, period):
        self._period = period

    @property
    def period(self):
        return self._period


@enum.unique
class AnalysisCallbackType(enum.Enum):
    TICK_CB = 'tick'


class Analysis:
    def __init__(self, state, conf, state_cbs):
        self._state = state
        self._conf = conf
        self._state_cbs = state_cbs
        self._period_key = None
        self._first_event_ts = None
        self._last_event_ts = None
        self._notification_cli_cbs = {}
        self._cbs = {}
        period_cbs = {
            core_period.PeriodEngineCallbackType.PERIOD_BEGIN:
                self._on_period_begin,
            core_period.PeriodEngineCallbackType.PERIOD_END:
                self._on_period_end,
        }
        self._period_engine = core_period.PeriodEngine(
            self._conf.period_def_registry, period_cbs)

        # This dict maps period objects (from the period module) to
        # period data objects. Period data objects are created by a
        # specific analysis implementing _create_period_data().
        self._period_data = {}

        self.started = False
        self.ended = False

    @property
    def first_event_ts(self):
        return self._first_event_ts

    @property
    def last_event_ts(self):
        return self._last_event_ts

    # Returns the period data object associated with a given period.
    def _get_period_data(self, period):
        return self._period_data.get(period)

    # Sets the period data object associated with a given period.
    def _set_period_data(self, period, data):
        self._period_data[period] = data

    # Removes the period data object associated with a given period.
    def _remove_period_data(self, period):
        del self._period_data[period]

    # Creates the unique "definition-less" period. This is used when
    # there are no user-specified periods.
    def _create_defless_period(self, evt):
        period = core_period.Period(None, None, evt, None)
        self._on_period_begin(period)

    # Returns the "definition-less" period.
    def _get_defless_period(self):
        if len(self._period_data) == 0:
            return

        return next(iter(self._period_data.keys()))

    # Removes the "definition-less" period.
    def _remove_defless_period(self, completed, evt):
        period = self._get_defless_period()

        if period is None:
            return

        period.end_evt = evt
        period.completed = completed
        self._on_period_end(period)
        assert(len(self._period_data) == 0)

    # Creates a fresh specific period data object. This must be
    # implemented by a specific analysis.
    def _create_period_data(self):
        raise NotImplementedError()

    def _begin_period_cb(self, period_data):
        pass

    def _end_period_cb(self, period_data, completed,
                       begin_captures, end_captures):
        pass

    # This is called back by the period engine when a new period is
    # created. `period` is the created period, and `evt` is the event
    # that triggered the beginning of this period (the original event,
    # while `period.begin_evt` is a copy of this event).
    def _on_period_begin(self, period):
        # create the specific analysis's period data object
        period_data = self._create_period_data()

        # associate the period data object to this period object
        period_data._set_period(period)
        self._set_period_data(period, period_data)

        # register state notification callbacks with this period data object
        self._state.register_notification_cbs(period_data, self._state_cbs)

        # call specific analysis's beginning of period callback
        self._begin_period_cb(period_data)

    # This is called back by the period engine when a period is finished,
    # or closed.
    #
    # If `period.completed` is True, then the period finishes because
    # its ending expression was satisfied by an event (`period.end_evt`).
    # Otherwise, the period finishes because one of its ancestors finishes,
    # or because the period engine user asked for it.
    def _on_period_end(self, period):
        # get the period data object associated with this period object
        period_data = self._get_period_data(period)

        # call specific analysis's end of period callback
        self._end_period_cb(period_data, period.completed,
                            period.begin_captures, period.end_captures)

        # send tick notification to owner (CLI)
        self._send_notification_cb(AnalysisCallbackType.TICK_CB, period_data,
                                   end_ns=self.last_event_ts)

        # clear registered state notification callbacks associated with
        # this period
        self._state.clear_period_notification_cbs(period_data)

        # remove this period data object
        self._remove_period_data(period)

    # This is called by the owner of this analysis when an event must
    # be processed (`ev`).
    def process_event(self, ev):
        self._check_analysis_end(ev)
        if self.ended:
            return

        if self._first_event_ts is None:
            self._first_event_ts = ev.timestamp

        self._last_event_ts = ev.timestamp

        if not self.started:
            if self._conf.begin_ts:
                self._check_analysis_begin(ev)
                if not self.started:
                    return
            else:
                self.started = True

        # Run the period engine. This call has the effect of calling
        # back _on_period_begin() or _on_period_end(), zero or more
        # times, for each beginning and ending period according to the
        # registered period definitions.
        self._period_engine.process_event(ev)

        # check the refresh period conditions
        self._check_refresh(ev)

    # Called by the owner of this analysis to indicate that this
    # analysis is starting.
    def begin_analysis(self, evt):
        # If we do not have any period defined, create the
        # "definition-less" period starting at the first event.
        if (self._conf.period_def_registry.is_empty and
                self._conf.begin_ts is None):
            self._create_defless_period(evt)

    def end_analysis(self):
        # let the periods know that it is the last one
        self.ended = True

        # This is the end of the analysis, so we need to remove all
        # the existing periods. This means either remove all the existing
        # periods in the period engine, or remove the unique,
        # "definition-less" period created here.
        if self._conf.period_def_registry.is_empty:
            self._remove_defless_period(False, None)
        else:
            self._period_engine.remove_all_periods()
            self._period_data.clear()

        # Send an empty TICK notification if the CLI needs to
        # do something at the end even if there are no existing
        # periods.
        self._send_notification_cb(AnalysisCallbackType.TICK_CB, None,
                                   end_ns=self._last_event_ts)

    def register_notification_cbs(self, cbs):
        for name in cbs:
            if name not in self._notification_cli_cbs:
                self._notification_cli_cbs[name] = []

            self._notification_cli_cbs[name].append(cbs[name])

    def _send_notification_cb(self, name, period, **kwargs):
        if name in self._notification_cli_cbs:
            for cb in self._notification_cli_cbs[name]:
                cb(period, **kwargs)

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
            self._create_defless_period(ev)
            self.started = True

    def _check_analysis_end(self, ev):
        if self._conf.end_ts and ev.timestamp > self._conf.end_ts:
            self.ended = True

    def _check_refresh(self, evt):
        if self._conf.refresh_period is None:
            return

        period = self._get_defless_period()

        if evt.timestamp >= (period.begin_evt.timestamp +
                             self._conf.refresh_period):
            # remove the current period and create a new one
            self._remove_defless_period(True, evt)
            self._create_defless_period(evt)

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
