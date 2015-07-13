#!/usr/bin/env python3
#
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

from ..linuxautomaton import automaton
from .. import __version__
from . import progressbar
from ..linuxautomaton import common
from babeltrace import TraceCollection
import argparse
import sys
import subprocess


class Command:
    def __init__(self, add_arguments_cb,
                 enable_proc_filter_args=False,
                 enable_max_min_args=False,
                 enable_max_min_size_arg=False,
                 enable_freq_arg=False,
                 enable_log_arg=False,
                 enable_stats_arg=False):
        self._add_arguments_cb = add_arguments_cb
        self._enable_proc_filter_args = enable_proc_filter_args
        self._enable_max_min_arg = enable_max_min_args
        self._enable_max_min_size_arg = enable_max_min_size_arg
        self._enable_freq_arg = enable_freq_arg
        self._enable_log_arg = enable_log_arg
        self._enable_stats_arg = enable_stats_arg
        self._create_automaton()

    def _error(self, msg, exit_code=1):
        print(msg, file=sys.stderr)
        sys.exit(exit_code)

    def _gen_error(self, msg, exit_code=1):
        self._error('Error: {}'.format(msg), exit_code)

    def _cmdline_error(self, msg, exit_code=1):
        self._error('Command line error: {}'.format(msg), exit_code)

    def _open_trace(self):
        traces = TraceCollection()
        handles = traces.add_traces_recursive(self._arg_path, 'ctf')
        if handles == {}:
            self._gen_error('Failed to open ' + self._arg_path, -1)
        self._handles = handles
        self._traces = traces
        self._process_date_args()
        if not self._arg_skip_validation:
            self._check_lost_events()

    def _close_trace(self):
        for handle in self._handles.values():
            self._traces.remove_trace(handle)

    def _check_lost_events(self):
        print('Checking the trace for lost events...')
        try:
            subprocess.check_output('babeltrace %s' % self._arg_path,
                                    shell=True)
        except subprocess.CalledProcessError:
            print('Error running babeltrace on the trace, cannot verify if '
                  'events were lost during the trace recording')

    def _run_analysis(self, reset_cb, refresh_cb, break_cb=None):
        self.trace_start_ts = 0
        self.trace_end_ts = 0
        self.current_sec = 0
        self.start_ns = 0
        self.end_ns = 0
        started = False
        progressbar.progressbar_setup(self)
        if not self._arg_begin:
            started = True
        for event in self._traces.events:
            progressbar.progressbar_update(self)
            if self._arg_begin and not started and \
                    event.timestamp >= self._arg_begin:
                started = True
                self.trace_start_ts = event.timestamp
                self.start_ns = event.timestamp
                reset_cb(event.timestamp)
            if self._arg_end and event.timestamp > self._arg_end:
                if break_cb is not None:
                    # check if we really can break here
                    if break_cb():
                        break
                else:
                    break
            if self.start_ns == 0:
                self.start_ns = event.timestamp
            if self.trace_start_ts == 0:
                self.trace_start_ts = event.timestamp
            self.end_ns = event.timestamp
            self._check_refresh(event, refresh_cb)
            self.trace_end_ts = event.timestamp
            # feed analysis
            self._analysis.process_event(event)
            # feed automaton
            self._automaton.process_event(event)
        progressbar.progressbar_finish(self)

    def _check_refresh(self, event, refresh_cb):
        """Check if we need to output something"""
        if self._arg_refresh is None:
            return
        event_sec = event.timestamp / common.NSEC_PER_SEC
        if self.current_sec == 0:
            self.current_sec = event_sec
        elif self.current_sec != event_sec and \
                (self.current_sec + self._arg_refresh) <= event_sec:
            refresh_cb(self.start_ns, event.timestamp)
            self.current_sec = event_sec
            self.start_ns = event.timestamp

    def _print_date(self, begin_ns, end_ns):
        date = 'Timerange: [%s, %s]' % (
            common.ns_to_hour_nsec(begin_ns, gmt=self._arg_gmt,
                                   multi_day=True),
            common.ns_to_hour_nsec(end_ns, gmt=self._arg_gmt,
                                   multi_day=True))
        print(date)

    def _validate_transform_common_args(self, args):
        self._arg_path = args.path

        if args.limit:
            self._arg_limit = args.limit

        self._arg_begin = None
        if args.begin:
            self._arg_begin = args.begin

        self._arg_end = None
        if args.end:
            self._arg_end = args.end

        self._arg_timerange = None
        if args.timerange:
            self._arg_timerange = args.timerange

        self._arg_gmt = None
        if args.gmt:
            self._arg_gmt = args.gmt

        self._arg_refresh = args.refresh
        self._arg_no_progress = args.no_progress
        self._arg_skip_validation = args.skip_validation

        if self._enable_proc_filter_args:
            self._arg_proc_list = None
            if args.procname:
                self._arg_proc_list = args.procname.split(',')

            self._arg_pid_list = None
            if args.pid:
                self._arg_pid_list = args.pid.split(',')
                self._arg_pid_list = [int(pid) for pid in self._arg_pid_list]

        if self._enable_max_min_arg:
            self._arg_max = args.max
            self._arg_min = args.min

        if self._enable_max_min_size_arg:
            self._arg_maxsize = args.maxsize
            self._arg_minsize = args.minsize

        if self._enable_freq_arg:
            self._arg_freq = args.freq
            self._arg_freq_resolution = args.freq_resolution

        if self._enable_log_arg:
            self._arg_log = args.log

        if self._enable_stats_arg:
            self._arg_stats = args.stats

    def _parse_args(self):
        ap = argparse.ArgumentParser(description=self._DESC)

        # common arguments
        ap.add_argument('path', metavar='<path/to/trace>', help='trace path')
        ap.add_argument('-r', '--refresh', type=int,
                        help='Refresh period in seconds')
        ap.add_argument('--limit', type=int, default=10,
                        help='Limit to top X (default = 10)')
        ap.add_argument('--no-progress', action='store_true',
                        help='Don\'t display the progress bar')
        ap.add_argument('--skip-validation', action='store_true',
                        help='Skip the trace validation')
        ap.add_argument('--gmt', action='store_true',
                        help='Manipulate timestamps based on GMT instead '
                             'of local time')
        ap.add_argument('--begin', type=str, help='start time: '
                                                  'hh:mm:ss[.nnnnnnnnn]')
        ap.add_argument('--end', type=str, help='end time: '
                                                'hh:mm:ss[.nnnnnnnnn]')
        ap.add_argument('--timerange', type=str, help='time range: '
                                                      '[begin,end]')

        if self._enable_proc_filter_args:
            ap.add_argument('--procname', type=str,
                            help='Filter the results only for this list of '
                                 'process names')
            ap.add_argument('--pid', type=str,
                            help='Filter the results only for this list '
                                 'of PIDs')

        if self._enable_max_min_arg:
            ap.add_argument('--max', type=float,
                            help='Filter out, duration longer than max usec')
            ap.add_argument('--min', type=float,
                            help='Filter out, duration shorter than min usec')

        if self._enable_max_min_size_arg:
            ap.add_argument('--maxsize', type=float,
                            help='Filter out, I/O operations working with '
                                 'more that maxsize bytes')
            ap.add_argument('--minsize', type=float,
                            help='Filter out, I/O operations working with '
                                 'less that minsize bytes')

        if self._enable_freq_arg:
            ap.add_argument('--freq', action='store_true',
                            help='Show the frequency distribution of '
                                 'handler duration')
            ap.add_argument('--freq-resolution', type=int, default=20,
                            help='Frequency distribution resolution '
                                 '(default 20)')

        if self._enable_log_arg:
            ap.add_argument('--log', action='store_true',
                            help='Display the events in the order they '
                                 'appeared')

        if self._enable_stats_arg:
            ap.add_argument('--stats', action='store_true',
                            help='Display the statistics')

        # specific arguments
        self._add_arguments_cb(ap)

        # version of the specific command
        ap.add_argument('-V', '--version', action='version',
                        version='LTTng Analyses v' + __version__)

        # parse arguments
        args = ap.parse_args()

        self._validate_transform_common_args(args)

        # save all arguments
        self._args = args

    def _process_date_args(self):
        self._arg_multi_day = common.is_multi_day_trace_collection(
            self._handles)
        if self._arg_timerange:
            (self._arg_begin, self._arg_end) = \
                common.extract_timerange(self._handles, self._arg_timerange,
                                         self._arg_gmt)
            if self._arg_begin is None or self._arg_end is None:
                print('Invalid timeformat')
                sys.exit(1)
        else:
            if self._arg_begin:
                self._arg_begin = common.date_to_epoch_nsec(self._handles,
                                                            self._arg_begin,
                                                            self._arg_gmt)
                if self._arg_begin is None:
                    print('Invalid timeformat')
                    sys.exit(1)
            if self._arg_end:
                self._arg_end = common.date_to_epoch_nsec(self._handles,
                                                          self._arg_end,
                                                          self._arg_gmt)
                if self._arg_end is None:
                    print('Invalid timeformat')
                    sys.exit(1)

                # We have to check if timestamp_begin is None, which
                # it always is in older versions of babeltrace. In
                # that case, the test is simply skipped and an invalid
                # --end value will cause an empty analysis
                if self._traces.timestamp_begin is not None and \
                   self._arg_end < self._traces.timestamp_begin:
                    print('--end timestamp before beginning of trace')
                    sys.exit(1)

    def _create_automaton(self):
        self._automaton = automaton.Automaton()
        self.state = self._automaton.state

    def _filter_process(self, proc):
        if self._arg_proc_list and proc.comm not in self._arg_proc_list:
            return False
        if self._arg_pid_list and proc.pid not in self._arg_pid_list:
            return False
        return True
