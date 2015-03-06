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

from .command import Command
import lttnganalyses.syscalls
from linuxautomaton import common
import operator
import statistics
import errno


class SyscallsAnalysis(Command):
    _VERSION = '0.1.0'
    _DESC = """The I/O command."""

    def __init__(self):
        super().__init__(self._add_arguments,
                         enable_proc_filter_args=True)
#                         enable_max_min_args=True,
#                         enable_max_min_size_arg=True,
#                         enable_freq_arg=True,
#                         enable_log_arg=True,
#                         enable_stats_arg=True)

    def _validate_transform_args(self):
        pass

    def run(self):
        # parse arguments first
        self._parse_args()
        # validate, transform and save specific arguments
        self._validate_transform_args()
        # open the trace
        self._open_trace()
        # create the appropriate analysis/analyses
        self._create_analysis()
        # run the analysis
        self._run_analysis(self._reset_total, self._refresh)
        # process the results
        self._compute_stats()
        # print results
        self._print_results(self.start_ns, self.trace_end_ts)
        # close the trace
        self._close_trace()

    def _create_analysis(self):
        self._analysis = lttnganalyses.syscalls.SyscallsAnalysis(self.state)

    def _compute_stats(self):
        pass

    def _refresh(self, begin, end):
        self._compute_stats()
        self._print_results(begin, end)
        self._reset_total(end)

    def filter_process(self, proc):
        if self._arg_proc_list and proc.comm not in self._arg_proc_list:
            return False
        if self._arg_pid_list and str(proc.pid) not in self._arg_pid_list:
            return False
        return True

    def _print_results(self, begin_ns, end_ns):
        print('Timerange: [%s, %s]' % (
            common.ns_to_hour_nsec(begin_ns, gmt=self._arg_gmt,
                                   multi_day=True),
            common.ns_to_hour_nsec(end_ns, gmt=self._arg_gmt,
                                   multi_day=True)))
        strformat = '{:<28} {:>14} {:>14} {:>14} {:>12} {:>10}  {:<14}'
        print('Per-TID syscalls statistics (usec)')
        for tid in sorted(self.state.tids.values(),
                          key=operator.attrgetter('total_syscalls'),
                          reverse=True):
            if not self.filter_process(tid):
                continue
            if tid.total_syscalls == 0:
                continue
            print(strformat.format('%s (%d, tid = %d)' % (
                tid.comm, tid.pid, tid.tid),
                'Count', 'Min', 'Average', 'Max', 'Stdev', 'Return values'))
            for syscall in sorted(tid.syscalls.values(),
                                  key=operator.attrgetter('count'),
                                  reverse=True):
                sysvalues = []
                rets = {}
                for s in syscall.rq:
                    sysvalues.append(s.duration)
                    if s.ret >= 0:
                        key = 'success'
                    else:
                        try:
                            key = errno.errorcode[-s.ret]
                        except:
                            key = str(s.ret)
                    if key in rets.keys():
                        rets[key] += 1
                    else:
                        rets[key] = 1
                if syscall.min is None:
                    syscallmin = '?'
                else:
                    syscallmin = '%0.03f' % (syscall.min / 1000)
                syscallmax = '%0.03f' % (syscall.max / 1000)
                syscallavg = '%0.03f' % \
                    (syscall.total_duration/(syscall.count*1000))
                if len(sysvalues) > 2:
                    stdev = '%0.03f' % (statistics.stdev(sysvalues) / 1000)
                else:
                    stdev = '?'
                name = syscall.name.replace('syscall_entry_', '')
                name = name.replace('sys_', '')
                print(strformat.format(' - ' + name, syscall.count,
                                       syscallmin, syscallavg, syscallmax,
                                       stdev, str(rets)))
            print(strformat.format('Total:', tid.total_syscalls, '', '', '',
                                   '', ''))
            print('-' * 113)

        print('\nTotal syscalls: %d' % (self.state.syscalls['total']))

    def _reset_total(self, start_ts):
        pass

    def _add_arguments(self, ap):
        # specific argument
        pass


# entry point
def run():
    # create command
    syscallscmd = SyscallsAnalysis()

    # execute command
    syscallscmd.run()
