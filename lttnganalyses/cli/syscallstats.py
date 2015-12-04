# The MIT License (MIT)
#
# Copyright (C) 2015 - Julien Desfossez <jdesfossez@efficios.com>
#               2015 - Antoine Busque <abusque@efficios.com>
#               2015 - Philippe Proulx <pproulx@efficios.com>
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

import errno
import operator
import statistics
from . import mi
from ..core import syscalls
from .command import Command


class SyscallsAnalysis(Command):
    _DESC = """The syscallstats command."""
    _ANALYSIS_CLASS = syscalls.SyscallsAnalysis
    _MI_TITLE = 'System call statistics'
    _MI_DESCRIPTION = 'Per-TID and global system call statistics'
    _MI_TAGS = [mi.Tags.SYSCALL, mi.Tags.STATS]
    _MI_TABLE_CLASS_PER_TID_STATS = 'per-tid'
    _MI_TABLE_CLASS_TOTAL = 'total'
    _MI_TABLE_CLASS_SUMMARY = 'summary'
    _MI_TABLE_CLASSES = [
        (
            _MI_TABLE_CLASS_PER_TID_STATS,
            'System call statistics', [
                ('syscall', 'System call', mi.Syscall),
                ('count', 'Call count', mi.Integer, 'calls'),
                ('min_duration', 'Minimum call duration', mi.Duration),
                ('avg_duration', 'Average call duration', mi.Duration),
                ('max_duration', 'Maximum call duration', mi.Duration),
                ('stdev_duration', 'Call duration standard deviation',
                 mi.Duration),
                ('return_values', 'Return values count', mi.String),
            ]
        ),
        (
            _MI_TABLE_CLASS_TOTAL,
            'Per-TID system call statistics', [
                ('process', 'Process', mi.Process),
                ('count', 'Total system call count', mi.Integer, 'calls'),
            ]
        ),
        (
            _MI_TABLE_CLASS_SUMMARY,
            'System call statistics - summary', [
                ('time_range', 'Time range', mi.TimeRange),
                ('process', 'Process', mi.Process),
                ('count', 'Total system call count', mi.Integer, 'calls'),
            ]
        ),
    ]

    def _analysis_tick(self, begin_ns, end_ns):
        total_table, per_tid_tables = self._get_result_tables(begin_ns, end_ns)

        if self._mi_mode:
            self._mi_append_result_tables(per_tid_tables)
            self._mi_append_result_table(total_table)
        else:
            self._print_date(begin_ns, end_ns)
            self._print_results(total_table, per_tid_tables)

    def _post_analysis(self):
        if not self._mi_mode:
            return

        if len(self._mi_get_result_tables(self._MI_TABLE_CLASS_TOTAL)) > 1:
            self._create_summary_result_table()

        self._mi_print()

    def _create_summary_result_table(self):
        total_tables = self._mi_get_result_tables(self._MI_TABLE_CLASS_TOTAL)
        begin = total_tables[0].timerange.begin
        end = total_tables[-1].timerange.end
        summary_table = \
            self._mi_create_result_table(self._MI_TABLE_CLASS_SUMMARY,
                                         begin, end)

        for total_table in total_tables:
            for row in total_table.rows:
                process = row.process
                count = row.count
                summary_table.append_row(
                    time_range=total_table.timerange,
                    process=process,
                    count=count,
                )

        self._mi_clear_result_tables()
        self._mi_append_result_table(summary_table)

    def _get_result_tables(self, begin_ns, end_ns):
        per_tid_tables = []
        total_table = self._mi_create_result_table(self._MI_TABLE_CLASS_TOTAL,
                                                   begin_ns, end_ns)

        for proc_stats in sorted(self._analysis.tids.values(),
                                 key=operator.attrgetter('total_syscalls'),
                                 reverse=True):
            if proc_stats.total_syscalls == 0:
                continue

            pid = proc_stats.pid

            if proc_stats.pid is None:
                pid = '?'

            subtitle = '%s (%s, TID: %d)' % (proc_stats.comm, pid,
                                             proc_stats.tid)
            result_table = \
                self._mi_create_result_table(
                    self._MI_TABLE_CLASS_PER_TID_STATS, begin_ns, end_ns,
                    subtitle)

            for syscall in sorted(proc_stats.syscalls.values(),
                                  key=operator.attrgetter('count'),
                                  reverse=True):
                durations = []
                return_count = {}

                for syscall_event in syscall.syscalls_list:
                    durations.append(syscall_event.duration)

                    if syscall_event.ret >= 0:
                        return_key = 'success'
                    else:
                        try:
                            return_key = errno.errorcode[-syscall_event.ret]
                        except KeyError:
                            return_key = str(syscall_event.ret)

                    if return_key not in return_count:
                        return_count[return_key] = 1

                    return_count[return_key] += 1

                if len(durations) > 2:
                    stdev = mi.Duration(statistics.stdev(durations))
                else:
                    stdev = mi.Unknown()

                result_table.append_row(
                    syscall=mi.Syscall(syscall.name),
                    count=mi.Integer(syscall.count),
                    min_duration=mi.Duration(syscall.min_duration),
                    avg_duration=mi.Duration(syscall.total_duration /
                                             syscall.count),
                    max_duration=mi.Duration(syscall.max_duration),
                    stdev_duration=stdev,
                    return_values=mi.String(str(return_count)),
                )

            per_tid_tables.append(result_table)
            total_table.append_row(
                process=mi.Process(proc_stats.comm, pid=proc_stats.pid,
                                   tid=proc_stats.tid),
                count=mi.Integer(proc_stats.total_syscalls),
            )

        return total_table, per_tid_tables

    def _print_results(self, total_table, per_tid_tables):
        line_format = '{:<38} {:>14} {:>14} {:>14} {:>12} {:>10}  {:<14}'

        print('Per-TID syscalls statistics (usec)')
        total_calls = 0

        for total_row, table in zip(total_table.rows, per_tid_tables):
            print(line_format.format(table.subtitle,
                                     'Count', 'Min', 'Average', 'Max',
                                     'Stdev', 'Return values'))
            for row in table.rows:
                syscall_name = row.syscall.name
                syscall_count = row.count.value
                min_duration = round(row.min_duration.to_us(), 3)
                avg_duration = round(row.avg_duration.to_us(), 3)
                max_duration = round(row.max_duration.to_us(), 3)

                if type(row.stdev_duration) is mi.Unknown:
                    stdev = '?'
                else:
                    stdev = round(row.stdev_duration.to_us(), 3)

                proc_total_calls = total_row.count.value
                print(line_format.format(
                    ' - ' + syscall_name, syscall_count, min_duration,
                    avg_duration, max_duration, stdev,
                    row.return_values.value))

            print(line_format.format('Total:', proc_total_calls,
                                     '', '', '', '', ''))
            print('-' * 113)
            total_calls += proc_total_calls

        print('\nTotal syscalls: %d' % (total_calls))

    def _add_arguments(self, ap):
        Command._add_proc_filter_args(ap)


def _run(mi_mode):
    syscallscmd = SyscallsAnalysis(mi_mode=mi_mode)
    syscallscmd.run()


# entry point (human)
def run():
    _run(mi_mode=False)


# entry point (MI)
def run_mi():
    _run(mi_mode=True)
