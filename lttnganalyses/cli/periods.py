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

import sys
import math
import operator
import statistics
import collections
from . import mi, termgraph
from ..core import periods
from .command import Command


_PeriodStats = collections.namedtuple('_PeriodStats', [
    'count',
    'min',
    'max',
    'stdev',
    'total',
])


class PeriodAnalysisCommand(Command):
    _DESC = """The periods command."""
    _ANALYSIS_CLASS = periods.PeriodAnalysis
    _MI_TITLE = 'Periods analysis'
    _MI_DESCRIPTION = \
        'Periods frequency distribution, statistics, top, and log'
    _MI_TAGS = [mi.Tags.PERIOD, mi.Tags.STATS, mi.Tags.FREQ, mi.Tags.TOP,
                mi.Tags.LOG]
    _MI_TABLE_CLASS_LOG = 'log'
    _MI_TABLE_CLASS_TOP = 'top'
    _MI_TABLE_CLASS_TOTAL_STATS = 'total_stats'
    _MI_TABLE_CLASS_PER_PERIOD_STATS = 'per_perio_stats'
    _MI_TABLE_CLASS_FREQ = 'freq'
    _MI_TABLE_CLASSES = [
        (
            _MI_TABLE_CLASS_LOG,
            'Period log', [
                ('begin_ts', 'Period begin timestamp', mi.Timestamp),
                ('end_ts', 'Period end timestamp', mi.Timestamp),
                ('duration', 'Period duration', mi.Duration),
                ('name', 'Period name', mi.String),
            ]
        ),
        (
            _MI_TABLE_CLASS_TOP,
            'Period top', [
                ('begin_ts', 'Period begin timestamp', mi.Timestamp),
                ('end_ts', 'Period end timestamp', mi.Timestamp),
                ('duration', 'Period duration', mi.Duration),
                ('name', 'Period name', mi.String),
            ]
        ),
        (
            _MI_TABLE_CLASS_TOTAL_STATS,
            'Period statistics', [
                ('count', 'Period count', mi.Number, 'occurences'),
                ('min_duration', 'Minimum duration', mi.Duration),
                ('avg_duration', 'Average duration', mi.Duration),
                ('max_duration', 'Maximum duration', mi.Duration),
                ('stdev_duration', 'Period duration standard deviation',
                 mi.Duration),
            ]
        ),
        (
            _MI_TABLE_CLASS_PER_PERIOD_STATS,
            'Period statistics', [
                ('name', 'Period name', mi.String),
                ('count', 'Period count', mi.Number, 'occurences'),
                ('min_duration', 'Minimum duration', mi.Duration),
                ('avg_duration', 'Average duration', mi.Duration),
                ('max_duration', 'Maximum duration', mi.Duration),
                ('stdev_duration', 'Period duration standard deviation',
                 mi.Duration),
            ]
        ),
        (
            _MI_TABLE_CLASS_FREQ,
            'Period duration frequency distribution', [
                ('duration_lower', 'Duration (lower bound)', mi.Duration),
                ('duration_upper', 'Duration (upper bound)', mi.Duration),
                ('count', 'Period count', mi.Number, 'occurences'),
            ]
        ),
    ]

    def _get_count(self, period_event):
        pass

    def _filter_duration(self, period_event):
        if self._args.min_duration is not None and \
                period_event.duration < (self._args.min_duration * 1000):
            return False
        if self._args.max_duration is not None and \
                period_event.duration > (self._args.max_duration * 1000):
            return False
        return True

    def _analysis_tick(self, period_data, end_ns):
        # We only output something at the end of the analysis
        # not when each period finishes
        if not self._analysis.ended:
            return

        # Override the timestamps since we are only interested in the
        # whole analysis timestamps, not the ones from the last period.
        begin_ns = self._analysis.first_event_ts
        end_ns = self._analysis.last_event_ts
        log_table = None
        top_table = None
        total_stats_table = None
        per_period_stats_table = None
        total_freq_tables = None
        per_period_freq_tables = None

        if self._args.log:
            log_table = self._get_log_result_table(begin_ns, end_ns)

        if self._args.top:
            top_table = self._get_top_result_table(begin_ns, end_ns)

        if self._args.stats:
            if self._args.total:
                total_stats_table = self._get_total_stats_result_table(
                    begin_ns, end_ns)

            if self._args.per_period:
                per_period_stats_table = \
                    self._get_per_period_stats_result_table(begin_ns, end_ns)

        if self._args.freq:
            if self._args.total:
                total_freq_tables = self._get_total_freq_result_tables(
                    begin_ns, end_ns)

            if self._args.per_period:
                per_period_freq_tables = \
                    self._get_per_period_freq_result_tables(begin_ns, end_ns)

        if self._mi_mode:
            if log_table:
                self._mi_append_result_table(log_table)

            if top_table:
                self._mi_append_result_table(top_table)

            if total_stats_table and total_stats_table.rows:
                self._mi_append_result_table(total_stats_table)

            if per_period_stats_table and per_period_stats_table.rows:
                self._mi_append_result_table(per_period_stats_table)

            if self._args.freq:
                if total_freq_tables:
                    self._mi_append_result_tables(total_freq_tables)

                if per_period_freq_tables:
                    self._mi_append_result_tables(per_period_freq_tables)
        else:
            self._print_date(begin_ns, end_ns)

            if self._args.stats:
                if total_stats_table:
                    self._print_total_stats(total_stats_table)
                if per_period_stats_table:
                    self._print_per_period_stats(per_period_stats_table)

            if self._args.freq:
                if total_freq_tables:
                    self._print_freq(total_freq_tables)
                if per_period_freq_tables:
                    self._print_freq(per_period_freq_tables)

            if log_table:
                self._print_period_events(log_table)

            if top_table:
                self._print_period_events(top_table)

    def _get_filtered_min_max_count_avg_total_flist(self, period_list):
        min = None
        max = None
        count = 0
        avg = 0
        total = 0
        filter_list = []
        for period_event in period_list:
            if not self._filter_duration(period_event):
                continue
            if min is None or min > period_event.duration:
                min = period_event.duration
            if max is None or max < period_event.duration:
                max = period_event.duration
            count += 1
            total += period_event.duration
            filter_list.append(period_event)
        if count > 0:
            avg = total/count
        else:
            avg = 0
        return min, max, count, avg, total, filter_list

    def _get_total_period_lists_stats(self):
        if self._args.min_duration is None and \
                self._args.max_duration is None:
            total_list = self._analysis.all_period_list
            stdev = self._compute_period_duration_stdev(total_list)
            total_stats = _PeriodStats(
                count=self._analysis.all_count,
                min=self._analysis.all_min_duration,
                max=self._analysis.all_max_duration,
                stdev=stdev,
                total=self._analysis.all_total_duration
            )
        else:
            min, max, count, avg, total, total_list = \
                self._get_filtered_min_max_count_avg_total_flist(
                    self._analysis.all_period_list)
            total_stats = _PeriodStats(
                count=count,
                min=min,
                max=max,
                stdev=self._compute_period_duration_stdev(total_list),
                total=total,
            )

        return [total_list], total_stats

    def _get_log_result_table(self, begin_ns, end_ns):
        result_table = self._mi_create_result_table(self._MI_TABLE_CLASS_LOG,
                                                    begin_ns, end_ns)
        for period_event in self._analysis.all_period_list:
            if not self._filter_duration(period_event):
                continue
            result_table.append_row(
                begin_ts=mi.Timestamp(period_event.start_ts),
                end_ts=mi.Timestamp(period_event.end_ts),
                duration=mi.Duration(period_event.duration),
                name=mi.String(period_event.name),
            )

        return result_table

    def _get_top_result_table(self, begin_ns, end_ns):
        result_table = self._mi_create_result_table(
            self._MI_TABLE_CLASS_TOP, begin_ns, end_ns)

        top_events = sorted(self._analysis.all_period_list,
                            key=operator.attrgetter('duration'),
                            reverse=True)
        top_events = top_events[:self._args.limit]

        for period_event in top_events:
            if not self._filter_duration(period_event):
                continue
            result_table.append_row(
                begin_ts=mi.Timestamp(period_event.start_ts),
                end_ts=mi.Timestamp(period_event.end_ts),
                duration=mi.Duration(period_event.duration),
                name=mi.String(period_event.name),
            )
        return result_table

    def _get_total_stats_result_table(self, begin_ns, end_ns):
        stats_table = \
            self._mi_create_result_table(self._MI_TABLE_CLASS_TOTAL_STATS,
                                         begin_ns, end_ns)

        if self._args.min_duration is None and \
                self._args.max_duration is None:
            stdev = self._compute_period_duration_stdev(
                self._analysis.all_period_list)
            count = self._analysis.all_count
            min = self._analysis.all_min_duration
            max = self._analysis.all_max_duration
            if count == 0:
                avg = 0
            else:
                avg = self._analysis.all_total_duration / \
                        self._analysis.all_count
        else:
            min, max, count, avg, total, period_list = \
                self._get_filtered_min_max_count_avg_total_flist(
                    self._analysis.all_period_list)
            stdev = self._compute_period_duration_stdev(period_list)

        if math.isnan(stdev):
            stdev = mi.Unknown()
        else:
            stdev = mi.Duration(stdev)

        avg = mi.Duration(avg)
        if min is None:
            min = mi.Duration(0)
        else:
            min = mi.Duration(min)

        if max is None:
            max = mi.Duration(0)
        else:
            max = mi.Duration(max)

        stats_table.append_row(
            count=mi.Number(count),
            min_duration=min,
            avg_duration=avg,
            max_duration=max,
            stdev_duration=stdev,
        )

        return stats_table

    def _get_per_period_stats_result_table(self, begin_ns, end_ns):
        stats_table = \
            self._mi_create_result_table(self._MI_TABLE_CLASS_PER_PERIOD_STATS,
                                         begin_ns, end_ns)

        period_stats_list = sorted(list(
            self._analysis.all_period_stats.values()),
            key=lambda period: period.name.lower())

        for period_stats in period_stats_list:
            if not period_stats.period_list:
                continue

            if self._args.min_duration is None and \
                    self._args.max_duration is None:
                stdev = self._compute_period_duration_stdev(
                    period_stats.period_list)
                min = period_stats.min_duration
                max = period_stats.max_duration
                count = period_stats.count
                if count > 0:
                    avg = period_stats.total_duration / \
                            period_stats.count
                else:
                    avg = 0
            else:
                min, max, count, avg, total, period_list = \
                    self._get_filtered_min_max_count_avg_total_flist(
                        period_stats.period_list)
                stdev = self._compute_period_duration_stdev(period_list)

            if math.isnan(stdev):
                stdev = mi.Unknown()
            else:
                stdev = mi.Duration(stdev)

            stats_table.append_row(
                name=mi.String(period_stats.name),
                count=mi.Number(count),
                min_duration=mi.Duration(min),
                avg_duration=mi.Duration(avg),
                max_duration=mi.Duration(max),
                stdev_duration=stdev,
            )

        return stats_table

    def _fill_freq_result_table(self, period_list, stats, min_duration,
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
            if min_duration is None:
                min_duration = 0
            else:
                min_duration /= 1000

            if max_duration is None:
                max_duration = 0
            else:
                max_duration /= 1000

            step = (max_duration - min_duration) / resolution

        if step == 0:
            return

        buckets = []
        counts = []

        for i in range(resolution):
            buckets.append(i * step)
            counts.append(0)

        for period_event in period_list:
            if not self._filter_duration(period_event):
                continue
            duration = period_event.duration / 1000
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
                count=mi.Number(count),
            )

    def _get_total_freq_result_tables(self, begin_ns, end_ns):
        freq_tables = []
        period_lists, period_stats = self._get_total_period_lists_stats()
        min_duration = None
        max_duration = None
        step = None
        subtitle = 'All periods'

        if self._args.freq_uniform:
            durations = []

            for period_list in period_lists:
                for period_event in period_list:
                    if not self._filter_duration(period_event):
                        continue
                    durations.append(period_event.duration)

            min_duration, max_duration, step = \
                self._get_uniform_freq_values(durations)

        for period_list in period_lists:
            freq_table = \
                self._mi_create_result_table(self._MI_TABLE_CLASS_FREQ,
                                             begin_ns, end_ns, subtitle)
            self._fill_freq_result_table(period_list, period_stats,
                                         min_duration, max_duration, step,
                                         freq_table)
            freq_tables.append(freq_table)

        return freq_tables

    def _get_period_lists_stats(self):
        period_lists = {}
        period_stats = {}

        for period in self._analysis.all_period_stats.keys():
            period_list = self._analysis.all_period_stats[period].period_list

            if not period_list:
                continue
            if self._args.min_duration is None and \
                    self._args.max_duration is None:
                stdev = self._compute_period_duration_stdev(period_list)
                count = len(period_list)
                min = self._analysis.all_period_stats[period].min_duration
                max = self._analysis.all_period_stats[period].max_duration
                total = \
                    self._analysis.all_period_stats[period].total_duration
            else:
                min, max, count, avg, total, period_list = \
                    self._get_filtered_min_max_count_avg_total_flist(
                        period_list)
                stdev = self._compute_period_duration_stdev(period_list)

            period_stats[period] = _PeriodStats(
                count=count,
                min=min,
                max=max,
                stdev=stdev,
                total=total,
            )
            period_lists[period] = period_list

        return period_lists, period_stats

    def _get_per_period_freq_result_tables(self, begin_ns, end_ns):
        freq_tables = []
        period_lists, period_stats = self._get_period_lists_stats()
        min_duration = None
        max_duration = None
        step = None

        if self._args.freq_uniform:
            durations = []

            for period_list in period_lists.values():
                for period_event in period_list:
                    if not self._filter_duration(period_event):
                        continue
                    durations.append(period_event.duration)

            min_duration, max_duration, step = \
                self._get_uniform_freq_values(durations)

        for period in sorted(period_stats.keys()):
            period_list = period_lists[period]
            stats = period_stats[period]
            subtitle = 'Period: {}'.format(period)
            freq_table = \
                self._mi_create_result_table(self._MI_TABLE_CLASS_FREQ,
                                             begin_ns, end_ns, subtitle)
            self._fill_freq_result_table(period_list, stats,
                                         min_duration, max_duration, step,
                                         freq_table)
            freq_tables.append(freq_table)

        return freq_tables

    def _compute_period_duration_stdev(self, period_events):
        period_durations = []
        for period_event in period_events:
            if not self._filter_duration(period_event):
                continue
            period_durations.append(period_event.duration)
        if len(period_durations) < 2:
            return float('nan')
        return statistics.stdev(period_durations)

    def _print_period_events(self, result_table):
        fmt = '[{:<18}, {:<18}] {:>15} {:<25}'
        title_fmt = '{:<20} {:<19} {:>15} {:<25}'
        print()
        print(result_table.title)
        print(title_fmt.format('Begin', 'End', 'Duration (us)', 'Name'))
        for row in result_table.rows:
            begin_ts = row.begin_ts.value
            end_ts = row.end_ts.value
            duration = row.duration.value
            name = row.name.value

            print(fmt.format(self._format_timestamp(begin_ts),
                             self._format_timestamp(end_ts),
                             '%0.03f' % (duration / 1000), name))

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
                if type(row.stdev_duration) is mi.Unknown:
                    stdev_str = '?'
                else:
                    stdev_str = '%0.03f' % row.stdev_duration.to_us()

                row_str = row_format.format(
                    '%d' % row.count.value,
                    '%0.03f' % row.min_duration.to_us(),
                    '%0.03f' % row.avg_duration.to_us(),
                    '%0.03f' % row.max_duration.to_us(),
                    '%s' % stdev_str,
                )

                print(row_str)

    def _print_per_period_stats(self, stats_table):
        row_format = '{:<25} {:>8}  {:>12}  {:>12}  {:>12}  {:>12}'
        header = row_format.format(
            'Period', 'Count', 'Min', 'Avg', 'Max', 'Stdev'
        )

        if stats_table.rows:
            print()
            print(stats_table.title + ' (us)')
            print(header)
            for row in stats_table.rows:
                if type(row.stdev_duration) is mi.Unknown:
                    stdev_str = '?'
                else:
                    stdev_str = '%0.03f' % row.stdev_duration.to_us()

                row_str = row_format.format(
                    '%s' % row.name,
                    '%d' % row.count.value,
                    '%0.03f' % row.min_duration.to_us(),
                    '%0.03f' % row.avg_duration.to_us(),
                    '%0.03f' % row.max_duration.to_us(),
                    '%s' % stdev_str,
                )

                print(row_str)

    def _print_frequency_distribution(self, freq_table):
        title_fmt = 'Periods duration frequency distribution - {}'

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

    def _validate_transform_args(self):
        args = self._args

        # If neither --total nor --per-period are specified, default
        # to --per-period
        if not (args.total or args.per_period):
            args.per_period = True

    def _add_arguments(self, ap):
        Command._add_min_max_args(ap)
        Command._add_freq_args(
            ap, help='Output the frequency distribution of sched switch '
            'durations')
        Command._add_top_args(ap, help='Output the top sched switch durations')
        Command._add_log_args(
            ap, help='Output the sched switches in chronological order')
        Command._add_stats_args(ap, help='Output sched switch statistics')
        ap.add_argument('--total', action='store_true',
                        help='Group all results (applies to stats and freq)')
        ap.add_argument('--per-period', action='store_true',
                        help='Group results per-period (applies to stats and '
                        'freq) (default)')
        ap.add_argument('--min-duration', type=float,
                        help='Filter out, periods shorter that duration '
                             '(usec)')
        ap.add_argument('--max-duration', type=float,
                        help='Filter out, periods longer than duration (usec)')


def _run(mi_mode):
    schedcmd = PeriodAnalysisCommand(mi_mode=mi_mode)
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
