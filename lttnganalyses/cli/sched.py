#!/usr/bin/env python3
#
# The MIT License (MIT)
#
# Copyright (C) 2015 - Julien Desfossez <jdesfossez@efficios.com>
#               2015 - Antoine Busque <abusque@efficios.com>
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
from ..core import sched
from ..linuxautomaton import common
from ..ascii_graph import Pyasciigraph
from . import mi
import math
import operator
import statistics
import sys


class SchedAnalysisCommand(Command):
    _DESC = """The sched command."""
    _ANALYSIS_CLASS = sched.SchedAnalysis
    _MI_TITLE = 'Scheduling latencies analysis'
    _MI_DESCRIPTION = \
        'Scheduling latencies frequency distribution, statistics, top, and log'
    _MI_TAGS = [mi.Tags.SCHED, mi.Tags.STATS, mi.Tags.FREQ, mi.Tags.TOP,
                mi.Tags.LOG]
    _MI_TABLE_CLASS_LOG = 'log'
    _MI_TABLE_CLASS_TOP = 'top'
    _MI_TABLE_CLASS_TOTAL_STATS = 'total_stats'
    _MI_TABLE_CLASS_PER_TID_STATS = 'per_tid_stats'
    _MI_TABLE_CLASS_PER_PRIO_STATS = 'per_prio_stats'
    # _MI_TABLE_CLASS_FREQ = 'freq'
    # _MI_TABLE_CLASS_SUMMARY = 'summary'
    _MI_TABLE_CLASSES = [
        (
            _MI_TABLE_CLASS_LOG,
            'Sched switch log', [
                ('wakeup_ts', 'Wakeup timestamp', mi.Timestamp),
                ('switch_ts', 'Switch timestamp', mi.Timestamp),
                ('latency', 'Scheduling latency', mi.Duration),
                ('prio', 'Priority', mi.Integer),
                ('wakee_proc', 'Wakee process', mi.Process),
                ('waker_proc', 'Waker process', mi.Process),
            ]
        ),
        (
            _MI_TABLE_CLASS_TOP,
            'Sched switch top', [
                ('wakeup_ts', 'Wakeup timestamp', mi.Timestamp),
                ('switch_ts', 'Switch timestamp', mi.Timestamp),
                ('latency', 'Scheduling latency', mi.Duration),
                ('prio', 'Priority', mi.Integer),
                ('wakee_proc', 'Wakee process', mi.Process),
                ('waker_proc', 'Waker process', mi.Process),
            ]
        ),
        (
            _MI_TABLE_CLASS_TOTAL_STATS,
            'Sched switch latency stats (total)', [
                ('count', 'Sched switch count', mi.Integer, 'sched switches'),
                ('min_latency', 'Minimum latency', mi.Duration),
                ('avg_latency', 'Average latency', mi.Duration),
                ('max_latency', 'Maximum latency', mi.Duration),
                ('stdev_latency', 'Scheduling latency standard deviation',
                 mi.Duration),
            ]
        ),
        (
            _MI_TABLE_CLASS_PER_TID_STATS,
            'Sched switch latency stats (per-TID)', [
                ('process', 'Wakee process', mi.Process),
                ('count', 'Sched switch count', mi.Integer, 'sched switches'),
                ('min_latency', 'Minimum latency', mi.Duration),
                ('avg_latency', 'Average latency', mi.Duration),
                ('max_latency', 'Maximum latency', mi.Duration),
                ('stdev_latency', 'Scheduling latency standard deviation',
                 mi.Duration),
            ]
        ),
        (
            _MI_TABLE_CLASS_PER_PRIO_STATS,
            'Sched switch latency stats (per-prio)', [
                ('prio', 'Priority', mi.Integer),
                ('count', 'Sched switch count', mi.Integer, 'sched switches'),
                ('min_latency', 'Minimum latency', mi.Duration),
                ('avg_latency', 'Average latency', mi.Duration),
                ('max_latency', 'Maximum latency', mi.Duration),
                ('stdev_latency', 'Scheduling latency standard deviation',
                 mi.Duration),
            ]
        ),
    ]

    def _analysis_tick(self, begin_ns, end_ns):
        log_table = None
        top_table = None
        total_stats_table = None
        per_tid_stats_table = None
        per_prio_stats_table = None

        if self._args.log:
            log_table = self._get_log_result_table(begin_ns, end_ns)

        if self._args.top:
            top_table = self._get_top_result_table(begin_ns, end_ns)

        if self._args.stats:
            if self._args.total:
                total_stats_table = self._get_total_stats_result_table(
                    begin_ns, end_ns)

            if self._args.per_tid:
                per_tid_stats_table = self._get_per_tid_stats_result_table(
                    begin_ns, end_ns)

            if self._args.per_prio:
                per_prio_stats_table = self._get_per_prio_stats_result_table(
                    begin_ns, end_ns)

        if self._mi_mode:
            if log_table:
                self._mi_append_result_table(log_table)

            if top_table:
                self._mi_append_result_table(top_table)

            if total_stats_table and total_stats_table.rows:
                self._mi_append_result_table(total_stats_table)

            if per_tid_stats_table and per_tid_stats_table.rows:
                self._mi_append_result_table(per_tid_stats_table)

            if per_prio_stats_table and per_prio_stats_table.rows:
                self._mi_append_result_table(per_prio_stats_table)
        else:
            self._print_date(begin_ns, end_ns)

            if self._args.stats:
                if total_stats_table:
                    self._print_total_stats(total_stats_table)
                if per_tid_stats_table:
                    self._print_per_tid_stats(per_tid_stats_table)
                if per_prio_stats_table:
                    self._print_per_prio_stats(per_prio_stats_table)

            if log_table:
                self._print_sched_events(log_table)

            if top_table:
                self._print_sched_events(top_table)

    def _get_log_result_table(self, begin_ns, end_ns):
        result_table = self._mi_create_result_table(self._MI_TABLE_CLASS_LOG,
                                                    begin_ns, end_ns)

        for sched_event in self._analysis.sched_list:
            wakee_proc = mi.Process(sched_event.wakee_proc.comm,
                                    sched_event.wakee_proc.pid,
                                    sched_event.wakee_proc.tid)

            if sched_event.waker_proc:
                waker_proc = mi.Process(sched_event.waker_proc.comm,
                                        sched_event.waker_proc.pid,
                                        sched_event.waker_proc.tid)
            else:
                waker_proc = mi.Empty()

            result_table.append_row(
                wakeup_ts=mi.Timestamp(sched_event.wakeup_ts),
                switch_ts=mi.Timestamp(sched_event.switch_ts),
                latency=mi.Duration(sched_event.latency),
                prio=mi.Integer(sched_event.prio),
                wakee_proc=wakee_proc,
                waker_proc=waker_proc,
            )

        return result_table

    def _get_top_result_table(self, begin_ns, end_ns):
        result_table = self._mi_create_result_table(self._MI_TABLE_CLASS_TOP    ,
                                                    begin_ns, end_ns)

        top_events = sorted(self._analysis.sched_list,
                            key=operator.attrgetter('latency'),
                            reverse=True)
        top_events = top_events[:self._args.limit]

        for sched_event in top_events:
            wakee_proc = mi.Process(sched_event.wakee_proc.comm,
                                    sched_event.wakee_proc.pid,
                                    sched_event.wakee_proc.tid)

            if sched_event.waker_proc:
                waker_proc = mi.Process(sched_event.waker_proc.comm,
                                        sched_event.waker_proc.pid,
                                        sched_event.waker_proc.tid)
            else:
                waker_proc = mi.Empty()

            result_table.append_row(
                wakeup_ts=mi.Timestamp(sched_event.wakeup_ts),
                switch_ts=mi.Timestamp(sched_event.switch_ts),
                latency=mi.Duration(sched_event.latency),
                prio=mi.Integer(sched_event.prio),
                wakee_proc=wakee_proc,
                waker_proc=waker_proc,
            )

        return result_table

    def _get_total_stats_result_table(self, begin_ns, end_ns):
        stats_table = \
            self._mi_create_result_table(self._MI_TABLE_CLASS_TOTAL_STATS,
                                         begin_ns, end_ns)

        stdev = self._compute_sched_latency_stdev(self._analysis.sched_list)
        if math.isnan(stdev):
            stdev = mi.Unknown()
        else:
            stdev = mi.Duration(stdev)

        stats_table.append_row(
            count=mi.Integer(self._analysis.count),
            min_latency=mi.Duration(self._analysis.min_latency),
            avg_latency=mi.Duration(self._analysis.total_latency /
                                    self._analysis.count),
            max_latency=mi.Duration(self._analysis.max_latency),
            stdev_latency=stdev,
        )

        return stats_table

    def _get_per_tid_stats_result_table(self, begin_ns, end_ns):
        stats_table = \
            self._mi_create_result_table(self._MI_TABLE_CLASS_PER_TID_STATS,
                                         begin_ns, end_ns)

        tid_stats_list = sorted(list(self._analysis.tids.values()),
                                key=operator.attrgetter('comm'))

        for tid_stats in tid_stats_list:
            if not tid_stats.sched_list:
                continue

            stdev = self._compute_sched_latency_stdev(tid_stats.sched_list)
            if math.isnan(stdev):
                stdev = mi.Unknown()
            else:
                stdev = mi.Duration(stdev)

            stats_table.append_row(
                process=mi.Process(tid=tid_stats.tid, name=tid_stats.comm),
                count=mi.Integer(tid_stats.count),
                min_latency=mi.Duration(tid_stats.min_latency),
                avg_latency=mi.Duration(tid_stats.total_latency /
                                        tid_stats.count),
                max_latency=mi.Duration(tid_stats.max_latency),
                stdev_latency=stdev,
            )

        return stats_table

    def _get_per_prio_stats_result_table(self, begin_ns, end_ns):
        stats_table = \
            self._mi_create_result_table(self._MI_TABLE_CLASS_PER_PRIO_STATS,
                                         begin_ns, end_ns)

        prio_sched_lists = {}
        for sched_event in self._analysis.sched_list:
            if sched_event.prio not in prio_sched_lists:
                prio_sched_lists[sched_event.prio] = []

            prio_sched_lists[sched_event.prio].append(sched_event)

        for prio in sorted(prio_sched_lists):
            sched_list = prio_sched_lists[prio]
            if not sched_list:
                continue

            stdev = self._compute_sched_latency_stdev(sched_list)
            if math.isnan(stdev):
                stdev = mi.Unknown()
            else:
                stdev = mi.Duration(stdev)

            latencies = [sched.latency for sched in sched_list]
            count = len(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            total_latency = sum(latencies)

            stats_table.append_row(
                prio=mi.Integer(prio),
                count=mi.Integer(count),
                min_latency=mi.Duration(min_latency),
                avg_latency=mi.Duration(total_latency / count),
                max_latency=mi.Duration(max_latency),
                stdev_latency=stdev,
            )

        return stats_table

    def _compute_sched_latency_stdev(self, sched_events):
        if len(sched_events) < 2:
            return float('nan')

        sched_latencies = []
        for sched_event in sched_events:
            sched_latencies.append(sched_event.latency)

        return statistics.stdev(sched_latencies)

    def _ns_to_hour_nsec(self, ts):
        return common.ns_to_hour_nsec(ts, self._args.multi_day, self._args.gmt)

    def _print_sched_events(self, result_table):
        fmt = '[{:<18}, {:<18}] {:>15} {:>10} {:<25}  {:<25}'
        title_fmt = '{:<20} {:<19} {:>15} {:>10} {:<25}  {:<25}'
        print()
        print(result_table.title)
        print(title_fmt.format('Wakeup', 'Switch', 'Latency (us)', 'Priority',
                               'Wakee', 'Waker'))
        for row in result_table.rows:
            wakeup_ts = row.wakeup_ts.value
            switch_ts = row.switch_ts.value
            latency = row.latency.value
            prio = row.prio.value
            wakee_proc = row.wakee_proc
            waker_proc = row.waker_proc

            wakee_str = '%s (%d)' % (wakee_proc.name, wakee_proc.tid)
            if isinstance(waker_proc, mi.Empty):
                waker_str = 'Unknown (N/A)'
            else:
                waker_str = '%s (%d)' % (waker_proc.name, waker_proc.tid)

            print(fmt.format(self._ns_to_hour_nsec(wakeup_ts),
                             self._ns_to_hour_nsec(switch_ts),
                             '%0.03f' % (latency / 1000), prio,
                             wakee_str, waker_str))

    def _print_total_stats(self, stats_table):
        row_format = '{:<12} {:<12} {:<12} {:<12} {:<12}'
        header = row_format.format(
            'Count', 'Min', 'Avg', 'Max', 'Stdev'
        )

        if stats_table.rows:
            print()
            print(stats_table.title + ' (us)')
            print(header)
            for row in stats_table.rows:
                if type(row.stdev_latency) is mi.Unknown:
                    stdev_str = '?'
                else:
                    stdev_str = '%0.03f' % row.stdev_latency.to_us()

                row_str = row_format.format(
                    '%d' % row.count.value,
                    '%0.03f' % row.min_latency.to_us(),
                    '%0.03f' % row.avg_latency.to_us(),
                    '%0.03f' % row.max_latency.to_us(),
                    '%s' % stdev_str,
                )

                print(row_str)

    def _print_per_tid_stats(self, stats_table):
        row_format = '{:<25} {:>8}  {:>12}  {:>12}  {:>12}  {:>12}'
        header = row_format.format(
            'Process', 'Count', 'Min', 'Avg', 'Max', 'Stdev'
        )

        if stats_table.rows:
            print()
            print(stats_table.title + ' (us)')
            print(header)
            for row in stats_table.rows:
                if type(row.stdev_latency) is mi.Unknown:
                    stdev_str = '?'
                else:
                    stdev_str = '%0.03f' % row.stdev_latency.to_us()

                proc = row.process
                proc_str = '%s (%d)' % (proc.name, proc.tid)

                row_str = row_format.format(
                    '%s' % proc_str,
                    '%d' % row.count.value,
                    '%0.03f' % row.min_latency.to_us(),
                    '%0.03f' % row.avg_latency.to_us(),
                    '%0.03f' % row.max_latency.to_us(),
                    '%s' % stdev_str,
                )

                print(row_str)

    def _print_per_prio_stats(self, stats_table):
        row_format = '{:>4} {:>8}  {:>12}  {:>12}  {:>12}  {:>12}'
        header = row_format.format(
            'Prio', 'Count', 'Min', 'Avg', 'Max', 'Stdev'
        )

        if stats_table.rows:
            print()
            print(stats_table.title + ' (us)')
            print(header)
            for row in stats_table.rows:
                if type(row.stdev_latency) is mi.Unknown:
                    stdev_str = '?'
                else:
                    stdev_str = '%0.03f' % row.stdev_latency.to_us()

                row_str = row_format.format(
                    '%d' % row.prio.value,
                    '%d' % row.count.value,
                    '%0.03f' % row.min_latency.to_us(),
                    '%0.03f' % row.avg_latency.to_us(),
                    '%0.03f' % row.max_latency.to_us(),
                    '%s' % stdev_str,
                )

                print(row_str)

    def _validate_transform_args(self, args):
        # If neither --total nor --per-prio are specified, default
        # to --per-tid
        if not (args.total or args.per_prio):
            args.per_tid = True

    def _add_arguments(self, ap):
        Command._add_min_max_args(ap)
        Command._add_freq_args(
            ap, help='Output the frequency distribution of sched switch '
            'latencies')
        Command._add_top_args(ap, help='Output the top sched switch latencies')
        Command._add_log_args(
            ap, help='Output the sched switches in chronological order')
        Command._add_stats_args(ap, help='Output sched switch statistics')
        ap.add_argument('--total', action='store_true',
                        help='Group all results (applies to stats and freq)')
        ap.add_argument('--per-tid', action='store_true',
                        help='Group results per-TID (applies to stats and '
                        'freq) (default)')
        ap.add_argument('--per-prio', action='store_true',
                        help='Group results per-prio (applies to stats and '
                        'freq)')


def _run(mi_mode):
    schedcmd = SchedAnalysisCommand(mi_mode=mi_mode)
    schedcmd.run()


def _runstats(mi_mode):
    sys.argv.insert(1, '--stats')
    _run(mi_mode)


def _runlog(mi_mode):
    sys.argv.insert(1, '--log')
    _run(mi_mode)


def _runtop(mi_mode):
    sys.argv.insert(1, '--top')
    _run(mi_mode)


def _runfreq(mi_mode):
    sys.argv.insert(1, '--freq')
    _run(mi_mode)


def runstats():
    _runstats(mi_mode=False)


def runlog():
    _runlog(mi_mode=False)


def runtop():
    _runtop(mi_mode=False)


def runfreq():
    _runfreq(mi_mode=False)


def runstats_mi():
    _runstats(mi_mode=True)


def runlog_mi():
    _runlog(mi_mode=True)


def runtop_mi():
    _runtop(mi_mode=True)


def runfreq_mi():
    _runfreq(mi_mode=True)
