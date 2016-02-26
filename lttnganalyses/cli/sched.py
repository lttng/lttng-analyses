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

import sys
import math
import operator
import statistics
import collections
from . import mi
from . import termgraph
from ..core import sched
from .command import Command
from ..common import format_utils
from ..linuxautomaton import common


_SchedStats = collections.namedtuple('_SchedStats', [
    'count',
    'min',
    'max',
    'stdev',
    'total',
])


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
    _MI_TABLE_CLASS_FREQ = 'freq'
    # _MI_TABLE_CLASS_SUMMARY = 'summary'
    _MI_TABLE_CLASSES = [
        (
            _MI_TABLE_CLASS_LOG,
            'Scheduling log', [
                ('wakeup_ts', 'Wakeup timestamp', mi.Timestamp),
                ('switch_ts', 'Switch timestamp', mi.Timestamp),
                ('latency', 'Scheduling latency', mi.Duration),
                ('prio', 'Priority', mi.Integer),
                ('target_cpu', 'Target CPU', mi.Integer),
                ('wakee_proc', 'Wakee process', mi.Process),
                ('waker_proc', 'Waker process', mi.Process),
            ]
        ),
        (
            _MI_TABLE_CLASS_TOP,
            'Scheduling top', [
                ('wakeup_ts', 'Wakeup timestamp', mi.Timestamp),
                ('switch_ts', 'Switch timestamp', mi.Timestamp),
                ('latency', 'Scheduling latency', mi.Duration),
                ('prio', 'Priority', mi.Integer),
                ('target_cpu', 'Target CPU', mi.Integer),
                ('wakee_proc', 'Wakee process', mi.Process),
                ('waker_proc', 'Waker process', mi.Process),
            ]
        ),
        (
            _MI_TABLE_CLASS_TOTAL_STATS,
            'Scheduling latency stats (total)', [
                ('count', 'Scheduling count', mi.Integer, 'schedulings'),
                ('min_latency', 'Minimum latency', mi.Duration),
                ('avg_latency', 'Average latency', mi.Duration),
                ('max_latency', 'Maximum latency', mi.Duration),
                ('stdev_latency', 'Scheduling latency standard deviation',
                 mi.Duration),
            ]
        ),
        (
            _MI_TABLE_CLASS_PER_TID_STATS,
            'Scheduling latency stats (per-TID)', [
                ('process', 'Wakee process', mi.Process),
                ('count', 'Scheduling count', mi.Integer, 'schedulings'),
                ('min_latency', 'Minimum latency', mi.Duration),
                ('avg_latency', 'Average latency', mi.Duration),
                ('max_latency', 'Maximum latency', mi.Duration),
                ('stdev_latency', 'Scheduling latency standard deviation',
                 mi.Duration),
                ('prio_list', 'Chronological priorities', mi.String),
            ]
        ),
        (
            _MI_TABLE_CLASS_PER_PRIO_STATS,
            'Scheduling latency stats (per-prio)', [
                ('prio', 'Priority', mi.Integer),
                ('count', 'Scheduling count', mi.Integer, 'schedulings'),
                ('min_latency', 'Minimum latency', mi.Duration),
                ('avg_latency', 'Average latency', mi.Duration),
                ('max_latency', 'Maximum latency', mi.Duration),
                ('stdev_latency', 'Scheduling latency standard deviation',
                 mi.Duration),
            ]
        ),
        (
            _MI_TABLE_CLASS_FREQ,
            'Scheduling latency frequency distribution', [
                ('duration_lower', 'Duration (lower bound)', mi.Duration),
                ('duration_upper', 'Duration (upper bound)', mi.Duration),
                ('count', 'Scheduling count', mi.Integer, 'schedulings'),
            ]
        ),
    ]

    def _analysis_tick(self, begin_ns, end_ns):
        log_table = None
        top_table = None
        total_stats_table = None
        per_tid_stats_table = None
        per_prio_stats_table = None
        total_freq_tables = None
        per_tid_freq_tables = None
        per_prio_freq_tables = None

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

        if self._args.freq:
            if self._args.total:
                total_freq_tables = self._get_total_freq_result_tables(
                    begin_ns, end_ns)

            if self._args.per_tid:
                per_tid_freq_tables = self._get_per_tid_freq_result_tables(
                    begin_ns, end_ns)

            if self._args.per_prio:
                per_prio_freq_tables = self._get_per_prio_freq_result_tables(
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

            if self._args.freq_series:
                if total_freq_tables:
                    self._mi_append_result_tables(total_freq_tables)

                if per_tid_freq_tables:
                    per_tid_freq_tables = [
                        self._get_per_tid_freq_series_table(
                            per_tid_freq_tables)
                    ]

                    self._mi_append_result_tables(per_tid_freq_tables)

                if per_prio_freq_tables:
                    per_prio_freq_tables = [
                        self._get_per_prio_freq_series_table(
                            per_prio_freq_tables)
                    ]

                    self._mi_append_result_tables(per_prio_freq_tables)
        else:
            self._print_date(begin_ns, end_ns)

            if self._args.stats:
                if total_stats_table:
                    self._print_total_stats(total_stats_table)
                if per_tid_stats_table:
                    self._print_per_tid_stats(per_tid_stats_table)
                if per_prio_stats_table:
                    self._print_per_prio_stats(per_prio_stats_table)

            if self._args.freq:
                if total_freq_tables:
                    self._print_freq(total_freq_tables)
                if per_tid_freq_tables:
                    self._print_freq(per_tid_freq_tables)
                if per_prio_freq_tables:
                    self._print_freq(per_prio_freq_tables)

            if log_table:
                self._print_sched_events(log_table)

            if top_table:
                self._print_sched_events(top_table)

    def _get_total_sched_lists_stats(self):
        total_list = self._analysis.sched_list
        stdev = self._compute_sched_latency_stdev(total_list)
        total_stats = _SchedStats(
            count=self._analysis.count,
            min=self._analysis.min_latency,
            max=self._analysis.max_latency,
            stdev=stdev,
            total=self._analysis.total_latency
        )

        return [total_list], total_stats

    def _get_tid_sched_lists_stats(self):
        tid_sched_lists = {}
        tid_stats = {}

        for sched_event in self._analysis.sched_list:
            tid = sched_event.wakee_proc.tid
            if tid not in tid_sched_lists:
                tid_sched_lists[tid] = []

            tid_sched_lists[tid].append(sched_event)

        for tid in tid_sched_lists:
            sched_list = tid_sched_lists[tid]

            if not sched_list:
                continue

            stdev = self._compute_sched_latency_stdev(sched_list)
            latencies = [sched.latency for sched in sched_list]
            count = len(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            total_latency = sum(latencies)

            tid_stats[tid] = _SchedStats(
                count=count,
                min=min_latency,
                max=max_latency,
                stdev=stdev,
                total=total_latency,
            )

        return tid_sched_lists, tid_stats

    def _get_prio_sched_lists_stats(self):
        prio_sched_lists = {}
        prio_stats = {}

        for sched_event in self._analysis.sched_list:
            if sched_event.prio not in prio_sched_lists:
                prio_sched_lists[sched_event.prio] = []

            prio_sched_lists[sched_event.prio].append(sched_event)

        for prio in prio_sched_lists:
            sched_list = prio_sched_lists[prio]

            if not sched_list:
                continue

            stdev = self._compute_sched_latency_stdev(sched_list)
            latencies = [sched.latency for sched in sched_list]
            count = len(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            total_latency = sum(latencies)

            prio_stats[prio] = _SchedStats(
                count=count,
                min=min_latency,
                max=max_latency,
                stdev=stdev,
                total=total_latency,
            )

        return prio_sched_lists, prio_stats

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
                target_cpu=mi.Integer(sched_event.target_cpu),
                wakee_proc=wakee_proc,
                waker_proc=waker_proc,
            )

        return result_table

    def _get_top_result_table(self, begin_ns, end_ns):
        result_table = self._mi_create_result_table(
            self._MI_TABLE_CLASS_TOP, begin_ns, end_ns)

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
                target_cpu=mi.Integer(sched_event.target_cpu),
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
                                key=lambda proc: proc.comm.lower())

        for tid_stats in tid_stats_list:
            if not tid_stats.sched_list:
                continue

            stdev = self._compute_sched_latency_stdev(tid_stats.sched_list)
            if math.isnan(stdev):
                stdev = mi.Unknown()
            else:
                stdev = mi.Duration(stdev)

            prio_list = format_utils.format_prio_list(tid_stats.prio_list)

            stats_table.append_row(
                process=mi.Process(tid=tid_stats.tid, name=tid_stats.comm),
                count=mi.Integer(tid_stats.count),
                min_latency=mi.Duration(tid_stats.min_latency),
                avg_latency=mi.Duration(tid_stats.total_latency /
                                        tid_stats.count),
                max_latency=mi.Duration(tid_stats.max_latency),
                stdev_latency=stdev,
                prio_list=mi.String(prio_list),
            )

        return stats_table

    def _get_per_prio_stats_result_table(self, begin_ns, end_ns):
        stats_table = \
            self._mi_create_result_table(self._MI_TABLE_CLASS_PER_PRIO_STATS,
                                         begin_ns, end_ns)

        _, prio_stats = self._get_prio_sched_lists_stats()

        for prio in sorted(prio_stats):
            stats = prio_stats[prio]
            stdev = stats.stdev

            if math.isnan(stdev):
                stdev = mi.Unknown()
            else:
                stdev = mi.Duration(stdev)

            count = stats.count
            min_latency = stats.min
            max_latency = stats.max
            total_latency = stats.total

            stats_table.append_row(
                prio=mi.Integer(prio),
                count=mi.Integer(count),
                min_latency=mi.Duration(min_latency),
                avg_latency=mi.Duration(total_latency / count),
                max_latency=mi.Duration(max_latency),
                stdev_latency=stdev,
            )

        return stats_table

    def _get_per_tid_freq_series_table(self, freq_tables):
        if not freq_tables:
            return

        column_infos = [
            ('duration_lower', 'Duration (lower bound)', mi.Duration),
            ('duration_upper', 'Duration (upper bound)', mi.Duration),
        ]

        for index, freq_table in enumerate(freq_tables):
            column_infos.append((
                'tid{}'.format(index),
                freq_table.subtitle,
                mi.Integer,
                'schedulings'
            ))

        title = 'Scheduling latencies frequency distributions'
        table_class = mi.TableClass(None, title, column_infos)
        begin = freq_tables[0].timerange.begin
        end = freq_tables[0].timerange.end
        result_table = mi.ResultTable(table_class, begin, end)

        for row_index, freq0_row in enumerate(freq_tables[0].rows):
            row_tuple = [
                freq0_row.duration_lower,
                freq0_row.duration_upper,
            ]

            for freq_table in freq_tables:
                freq_row = freq_table.rows[row_index]
                row_tuple.append(freq_row.count)

            result_table.append_row_tuple(tuple(row_tuple))

        return result_table

    def _get_per_prio_freq_series_table(self, freq_tables):
        if not freq_tables:
            return

        column_infos = [
            ('duration_lower', 'Duration (lower bound)', mi.Duration),
            ('duration_upper', 'Duration (upper bound)', mi.Duration),
        ]

        for index, freq_table in enumerate(freq_tables):
            column_infos.append((
                'prio{}'.format(index),
                freq_table.subtitle,
                mi.Integer,
                'schedulings'
            ))

        title = 'Scheduling latencies frequency distributions'
        table_class = mi.TableClass(None, title, column_infos)
        begin = freq_tables[0].timerange.begin
        end = freq_tables[0].timerange.end
        result_table = mi.ResultTable(table_class, begin, end)

        for row_index, freq0_row in enumerate(freq_tables[0].rows):
            row_tuple = [
                freq0_row.duration_lower,
                freq0_row.duration_upper,
            ]

            for freq_table in freq_tables:
                freq_row = freq_table.rows[row_index]
                row_tuple.append(freq_row.count)

            result_table.append_row_tuple(tuple(row_tuple))

        return result_table

    def _fill_freq_result_table(self, sched_list, stats, min_duration,
                                max_duration, step, freq_table):
        # The number of bins for the histogram
        resolution = self._args.freq_resolution

        if not self._args.freq_uniform:
            if self._args.min is not None:
                min_duration = self._args.min
            else:
                min_duration = stats.min

            if self._args.max is not None:
                max_duration = self._args.max
            else:
                max_duration = stats.max

            # ns to µs
            min_duration /= 1000
            max_duration /= 1000

            step = (max_duration - min_duration) / resolution

        if step == 0:
            return

        buckets = []
        counts = []

        for i in range(resolution):
            buckets.append(i * step)
            counts.append(0)

        for sched_event in sched_list:
            duration = sched_event.latency / 1000
            index = int((duration - min_duration) / step)

            if index >= resolution:
                # special case for max value: put in last bucket (includes
                # its upper bound)
                if duration == max_duration:
                    counts[index - 1] += 1

                continue

            counts[index] += 1

        for index, count in enumerate(counts):
            lower_bound = index * step + min_duration
            upper_bound = (index + 1) * step + min_duration
            freq_table.append_row(
                duration_lower=mi.Duration.from_us(lower_bound),
                duration_upper=mi.Duration.from_us(upper_bound),
                count=mi.Integer(count),
            )

    def _get_total_freq_result_tables(self, begin_ns, end_ns):
        freq_tables = []
        sched_lists, sched_stats = self._get_total_sched_lists_stats()
        min_duration = None
        max_duration = None
        step = None

        if self._args.freq_uniform:
            latencies = []

            for sched_list in sched_lists:
                latencies += [sched.latency for sched in sched_list]

            min_duration, max_duration, step = \
                self._get_uniform_freq_values(latencies)

        for sched_list in sched_lists:
            freq_table = \
                self._mi_create_result_table(self._MI_TABLE_CLASS_FREQ,
                                             begin_ns, end_ns)
            self._fill_freq_result_table(sched_list, sched_stats, min_duration,
                                         max_duration, step, freq_table)
            freq_tables.append(freq_table)

        return freq_tables

    def _get_per_tid_freq_result_tables(self, begin_ns, end_ns):
        freq_tables = []
        tid_sched_lists, tid_stats = self._get_tid_sched_lists_stats()
        min_duration = None
        max_duration = None
        step = None

        if self._args.freq_uniform:
            latencies = []

            for sched_list in tid_sched_lists.values():
                latencies += [sched.latency for sched in sched_list]

            min_duration, max_duration, step = \
                self._get_uniform_freq_values(latencies)

        for tid in sorted(tid_sched_lists):
            sched_list = tid_sched_lists[tid]
            stats = tid_stats[tid]
            subtitle = 'TID: {}'.format(tid)
            freq_table = \
                self._mi_create_result_table(self._MI_TABLE_CLASS_FREQ,
                                             begin_ns, end_ns, subtitle)
            self._fill_freq_result_table(sched_list, stats, min_duration,
                                         max_duration, step, freq_table)
            freq_tables.append(freq_table)

        return freq_tables

    def _get_per_prio_freq_result_tables(self, begin_ns, end_ns):
        freq_tables = []
        prio_sched_lists, prio_stats = self._get_prio_sched_lists_stats()
        min_duration = None
        max_duration = None
        step = None

        if self._args.freq_uniform:
            latencies = []

            for sched_list in prio_sched_lists.values():
                latencies += [sched.latency for sched in sched_list]

            min_duration, max_duration, step = \
                self._get_uniform_freq_values(latencies)

        for prio in sorted(prio_sched_lists):
            sched_list = prio_sched_lists[prio]
            stats = prio_stats[prio]
            subtitle = 'Priority: {}'.format(prio)
            freq_table = \
                self._mi_create_result_table(self._MI_TABLE_CLASS_FREQ,
                                             begin_ns, end_ns, subtitle)
            self._fill_freq_result_table(sched_list, stats, min_duration,
                                         max_duration, step, freq_table)
            freq_tables.append(freq_table)

        return freq_tables

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
        fmt = '[{:<18}, {:<18}] {:>15} {:>10}  {:>3}   {:<25}  {:<25}'
        title_fmt = '{:<20} {:<19} {:>15} {:>10}  {:>3}   {:<25}  {:<25}'
        print()
        print(result_table.title)
        print(title_fmt.format('Wakeup', 'Switch', 'Latency (us)', 'Priority',
                               'CPU', 'Wakee', 'Waker'))
        for row in result_table.rows:
            wakeup_ts = row.wakeup_ts.value
            switch_ts = row.switch_ts.value
            latency = row.latency.value
            prio = row.prio.value
            target_cpu = row.target_cpu.value
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
                             target_cpu, wakee_str, waker_str))

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
        row_format = '{:<25} {:>8}  {:>12}  {:>12}  {:>12}  {:>12}   {}'
        header = row_format.format(
            'Process', 'Count', 'Min', 'Avg', 'Max', 'Stdev', 'Priorities'
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
                    '%s' % row.prio_list.value,
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

    def _print_frequency_distribution(self, freq_table):
        title_fmt = 'Scheduling latency frequency distribution - {}'

        graph = termgraph.FreqGraph(
            data=freq_table.rows,
            get_value=lambda row: row.count.value,
            get_lower_bound=lambda row: row.duration_lower.to_us(),
            title=title_fmt.format(freq_table.subtitle),
            unit='µs'
        )

        graph.print_graph()

    def _print_freq(self, freq_tables):
        for freq_table in freq_tables:
            self._print_frequency_distribution(freq_table)

    def _validate_transform_args(self, args):
        # If neither --total nor --per-prio are specified, default
        # to --per-tid
        if not (args.total or args.per_prio):
            args.per_tid = True

    def _add_arguments(self, ap):
        Command._add_min_max_args(ap)
        Command._add_proc_filter_args(ap)
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
