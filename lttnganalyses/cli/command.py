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

from ..core import analysis
from ..linuxautomaton import automaton
from .. import __version__
from . import progressbar
from ..linuxautomaton import common
from babeltrace import TraceCollection
import argparse
import sys
import subprocess


class Command:
    def __init__(self):
        self._analysis = None
        self._analysis_conf = None
        self._args = None
        self._handles = None
        self._traces = None

        self._create_automaton()

    def run(self):
        self._parse_args()
        self._open_trace()
        self._create_analysis()
        self._run_analysis()
        self._close_trace()

    def _error(self, msg, exit_code=1):
        print(msg, file=sys.stderr)
        sys.exit(exit_code)

    def _gen_error(self, msg, exit_code=1):
        self._error('Error: {}'.format(msg), exit_code)

    def _cmdline_error(self, msg, exit_code=1):
        self._error('Command line error: {}'.format(msg), exit_code)

    def _open_trace(self):
        traces = TraceCollection()
        handles = traces.add_traces_recursive(self._args.path, 'ctf')
        if handles == {}:
            self._gen_error('Failed to open ' + self._args.path, -1)
        self._handles = handles
        self._traces = traces
        self._process_date_args()
        if not self._args.skip_validation:
            self._check_lost_events()

    def _close_trace(self):
        for handle in self._handles.values():
            self._traces.remove_trace(handle)

    def _check_lost_events(self):
        print('Checking the trace for lost events...')
        try:
            subprocess.check_output('babeltrace %s' % self._args.path,
                                    shell=True)
        except subprocess.CalledProcessError:
            print('Error running babeltrace on the trace, cannot verify if '
                  'events were lost during the trace recording')

    def _run_analysis(self):
        progressbar.progressbar_setup(self)

        for event in self._traces.events:
            progressbar.progressbar_update(self)
            self._analysis.process_event(event)
            if self._analysis.ended:
                break
            self._automaton.process_event(event)

        progressbar.progressbar_finish(self)
        self._analysis.end()

    def _print_date(self, begin_ns, end_ns):
        date = 'Timerange: [%s, %s]' % (
            common.ns_to_hour_nsec(begin_ns, gmt=self._args.gmt,
                                   multi_day=True),
            common.ns_to_hour_nsec(end_ns, gmt=self._args.gmt,
                                   multi_day=True))
        print(date)

    def _validate_transform_common_args(self, args):
        refresh_period_ns = None
        if args.refresh is not None:
            try:
                refresh_period_ns = common.duration_str_to_ns(args.refresh)
            except ValueError as e:
                self._cmdline_error(str(e))

        self._analysis_conf = analysis.AnalysisConfig()
        self._analysis_conf.refresh_period = refresh_period_ns
        self._analysis_conf.period_begin_ev_name = args.period_begin
        self._analysis_conf.period_end_ev_name = args.period_end

        # convert min/max args from µs to ns, if needed
        if hasattr(args, 'min') and args.min is not None:
            args.min *= 1000
            self._analysis_conf.min_duration = args.min
        if hasattr(args, 'max') and args.max is not None:
            args.max *= 1000
            self._analysis_conf.max_duration = args.max

        if hasattr(args, 'procname'):
            args.proc_list = None
            if args.procname:
                args.proc_list = args.procname.split(',')

        if hasattr(args, 'pid'):
            args.pid_list = None
            if args.pid:
                args.pid_list = args.pid.split(',')
                args.pid_list = [int(pid) for pid in args.pid_list]

    def _validate_transform_args(self, args):
        pass

    def _parse_args(self):
        ap = argparse.ArgumentParser(description=self._DESC)

        # common arguments
        ap.add_argument('path', metavar='<path/to/trace>', help='trace path')
        ap.add_argument('-r', '--refresh', type=str,
                        help='Refresh period, with optional units suffix '
                        '(default units: s)')
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
        ap.add_argument('--period-begin', type=str,
                        help='Analysis period start marker event name')
        ap.add_argument('--period-end', type=str,
                        help='Analysis period end marker event name '
                        '(requires --period-begin)')
        ap.add_argument('-V', '--version', action='version',
                        version='LTTng Analyses v' + __version__)

        # Used to add command-specific args
        self._add_arguments(ap)

        args = ap.parse_args()
        self._validate_transform_common_args(args)
        self._validate_transform_args(args)
        self._args = args

    @staticmethod
    def _add_proc_filter_args(ap):
        ap.add_argument('--procname', type=str,
                        help='Filter the results only for this list of '
                        'process names')
        ap.add_argument('--pid', type=str,
                        help='Filter the results only for this list of PIDs')

    @staticmethod
    def _add_min_max_args(ap):
        ap.add_argument('--min', type=float,
                        help='Filter out durations shorter than min usec')
        ap.add_argument('--max', type=float,
                        help='Filter out durations longer than max usec')

    @staticmethod
    def _add_freq_args(ap, help=None):
        if not help:
            help = 'Output the frequency distribution'

        ap.add_argument('--freq', action='store_true', help=help)
        ap.add_argument('--freq-resolution', type=int, default=20,
                        help='Frequency distribution resolution '
                        '(default 20)')

    @staticmethod
    def _add_log_args(ap, help=None):
        if not help:
            help = 'Output the events in chronological order'

        ap.add_argument('--log', action='store_true', help=help)

    @staticmethod
    def _add_stats_args(ap, help=None):
        if not help:
            help = 'Output statistics'

        ap.add_argument('--stats', action='store_true', help=help)

    def _add_arguments(self, ap):
        pass

    def _process_date_args(self):

        def date_to_epoch_nsec(date):
            ts = common.date_to_epoch_nsec(self._handles, date, self._args.gmt)
            if ts is None:
                self._cmdline_error('Invalid date format: "{}"'.format(date))

            return ts

        self._args.multi_day = common.is_multi_day_trace_collection(
            self._handles)
        if self._args.timerange:
            (self._analysis_conf.begin_ts, self._analysis_conf.end_ts) = \
                common.extract_timerange(self._handles, self._args.timerange,
                                         self._args.gmt)
            if self._args.begin is None or self._args.end is None:
                print('Invalid timeformat')
                sys.exit(1)
        else:
            if self._args.begin:
                self._args.begin = date_to_epoch_nsec(
                    self._args.begin)
            if self._args.end:
                self._analysis_conf.end_ts = date_to_epoch_nsec(
                    self._args.end)

                # We have to check if timestamp_begin is None, which
                # it always is in older versions of babeltrace. In
                # that case, the test is simply skipped and an invalid
                # --end value will cause an empty analysis
                if self._traces.timestamp_begin is not None and \
                   self._analysis_conf.end_ts < self._traces.timestamp_begin:
                    self._cmdline_error(
                        '--end timestamp before beginning of trace')

        self._analysis_conf.begin_ts = self._args.begin
        self._analysis_conf.end_ts = self._args.end

    def _create_analysis(self):
        notification_cbs = {
            'output_results': self._output_results
        }

        self._analysis = self._ANALYSIS_CLASS(self.state, self._analysis_conf)
        self._analysis.register_notification_cbs(notification_cbs)

    def _create_automaton(self):
        self._automaton = automaton.Automaton()
        self.state = self._automaton.state

    def _output_results(self, **kwargs):
        begin_ns = kwargs['begin_ns']
        end_ns = kwargs['end_ns']

        # TODO allow output of results to some other place/in other
        # format than plain text-cli
        self._print_results(begin_ns, end_ns)

    def _print_results(self, begin_ns, end_ns):
        raise NotImplementedError()

    def _filter_process(self, proc):
        if not proc:
            return True
        if self._args.proc_list and proc.comm not in self._args.proc_list:
            return False
        if self._args.pid_list and proc.pid not in self._args.pid_list:
            return False
        return True
