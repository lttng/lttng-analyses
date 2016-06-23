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

import itertools
import math
import statistics
import sys
from . import mi
from . import termgraph
from .command import Command
from ..core import irq as core_irq
from ..linuxautomaton import sv


class IrqAnalysisCommand(Command):
    _DESC = """The irq command."""
    _ANALYSIS_CLASS = core_irq.IrqAnalysis
    _MI_TITLE = 'System interrupt analysis'
    _MI_DESCRIPTION = 'Interrupt frequency distribution, statistics, and log'
    _MI_TAGS = [mi.Tags.INTERRUPT, mi.Tags.STATS, mi.Tags.FREQ, mi.Tags.LOG]
    _MI_TABLE_CLASS_LOG = 'log'
    _MI_TABLE_CLASS_HARD_STATS = 'hard-stats'
    _MI_TABLE_CLASS_SOFT_STATS = 'soft-stats'
    _MI_TABLE_CLASS_FREQ = 'freq'
    _MI_TABLE_CLASS_SUMMARY = 'summary'
    _MI_TABLE_CLASSES = [
        (
            _MI_TABLE_CLASS_LOG,
            'Interrupt log', [
                ('time_range', 'Time range', mi.TimeRange),
                ('raised_ts', 'Raised timestamp', mi.Timestamp),
                ('cpu', 'CPU', mi.Cpu),
                ('irq', 'Interrupt', mi.Irq),
            ]
        ),
        (
            _MI_TABLE_CLASS_HARD_STATS,
            'Hardware interrupt statistics', [
                ('irq', 'Interrupt', mi.Irq),
                ('count', 'Interrupt count', mi.Number, 'interrupts'),
                ('min_duration', 'Minimum duration', mi.Duration),
                ('avg_duration', 'Average duration', mi.Duration),
                ('max_duration', 'Maximum duration', mi.Duration),
                ('stdev_duration', 'Interrupt duration standard deviation',
                 mi.Duration),
            ]
        ),
        (
            _MI_TABLE_CLASS_SOFT_STATS,
            'Software interrupt statistics', [
                ('irq', 'Interrupt', mi.Irq),
                ('count', 'Interrupt count', mi.Number, 'interrupts'),
                ('min_duration', 'Minimum duration', mi.Duration),
                ('avg_duration', 'Average duration', mi.Duration),
                ('max_duration', 'Maximum duration', mi.Duration),
                ('stdev_duration', 'Interrupt duration standard deviation',
                 mi.Duration),
                ('raise_count', 'Interrupt raise count', mi.Number,
                 'interrupt raises'),
                ('min_latency', 'Minimum raise latency', mi.Duration),
                ('avg_latency', 'Average raise latency', mi.Duration),
                ('max_latency', 'Maximum raise latency', mi.Duration),
                ('stdev_latency', 'Interrupt raise latency standard deviation',
                 mi.Duration),
            ]
        ),
        (
            _MI_TABLE_CLASS_FREQ,
            'Interrupt handler duration frequency distribution', [
                ('duration_lower', 'Duration (lower bound)', mi.Duration),
                ('duration_upper', 'Duration (upper bound)', mi.Duration),
                ('count', 'Interrupt count', mi.Number, 'interrupts'),
            ]
        ),
        (
            _MI_TABLE_CLASS_SUMMARY,
            'Interrupt statistics - summary', [
                ('time_range', 'Time range', mi.TimeRange),
                ('count', 'Total interrupt count', mi.Number, 'interrupts'),
            ]
        ),
    ]

    def _analysis_tick(self, begin_ns, end_ns):
        log_table = None
        hard_stats_table = None
        soft_stats_table = None
        freq_tables = None

        if self._args.log:
            log_table = self._get_log_result_table(begin_ns, end_ns)

        if self._args.stats or self._args.freq:
            hard_stats_table, soft_stats_table, freq_tables = \
                self._get_stats_freq_result_tables(begin_ns, end_ns)

        if self._mi_mode:
            self._mi_append_result_table(log_table)
            self._mi_append_result_table(hard_stats_table)
            self._mi_append_result_table(soft_stats_table)

            if self._args.freq_series:
                freq_tables = [self._get_freq_series_table(freq_tables)]

            self._mi_append_result_tables(freq_tables)
        else:
            self._print_date(begin_ns, end_ns)

            if hard_stats_table or soft_stats_table or freq_tables:
                self._print_stats_freq(hard_stats_table, soft_stats_table,
                                       freq_tables)
                if log_table:
                    print()

            if log_table:
                self._print_log(log_table)

    def _create_summary_result_tables(self):
        if not self._args.stats:
            self._mi_clear_result_tables()
            return

        hard_stats_tables = \
            self._mi_get_result_tables(self._MI_TABLE_CLASS_HARD_STATS)
        soft_stats_tables = \
            self._mi_get_result_tables(self._MI_TABLE_CLASS_SOFT_STATS)
        assert len(hard_stats_tables) == len(soft_stats_tables)
        begin = hard_stats_tables[0].timerange.begin.value
        end = hard_stats_tables[-1].timerange.end.value
        summary_table = \
            self._mi_create_result_table(self._MI_TABLE_CLASS_SUMMARY,
                                         begin, end)

        for hs_table, ss_table in zip(hard_stats_tables, soft_stats_tables):
            assert hs_table.timerange == ss_table.timerange

            for row in itertools.chain(hs_table.rows, ss_table.rows):
                summary_table.append_row(
                    time_range=hs_table.timerange,
                    count=row.count,
                )

        self._mi_clear_result_tables()
        self._mi_append_result_table(summary_table)

    def _get_log_result_table(self, begin_ns, end_ns):
        result_table = self._mi_create_result_table(self._MI_TABLE_CLASS_LOG,
                                                    begin_ns, end_ns)

        for irq in self._analysis.irq_list:
            if not self._filter_irq(irq):
                continue

            if type(irq) is sv.HardIRQ:
                is_hard = True
                raised_ts_do = mi.Empty()
                name = self._analysis.hard_irq_stats[irq.id].name
            else:
                is_hard = False

                if irq.raise_ts is None:
                    raised_ts_do = mi.Unknown()
                else:
                    raised_ts_do = mi.Timestamp(irq.raise_ts)

                name = self._analysis.softirq_stats[irq.id].name

            result_table.append_row(
                time_range=mi.TimeRange(irq.begin_ts, irq.end_ts),
                raised_ts=raised_ts_do,
                cpu=mi.Cpu(irq.cpu_id),
                irq=mi.Irq(is_hard, irq.id, name),
            )

        return result_table

    def _get_common_stats_result_table_row(self, is_hard, irq_nr, irq_stats):
        stdev = self._compute_duration_stdev(irq_stats)

        if math.isnan(stdev):
            stdev = mi.Unknown()
        else:
            stdev = mi.Duration(stdev)

        return (
            mi.Irq(is_hard, irq_nr, irq_stats.name),
            mi.Number(irq_stats.count),
            mi.Duration(irq_stats.min_duration),
            mi.Duration(irq_stats.total_duration / irq_stats.count),
            mi.Duration(irq_stats.max_duration),
            stdev,
        )

    def _append_hard_stats_result_table_row(self, irq_nr, irq_stats,
                                            hard_stats_table):
        common_row = self._get_common_stats_result_table_row(True, irq_nr,
                                                             irq_stats)
        hard_stats_table.append_row(
            irq=common_row[0],
            count=common_row[1],
            min_duration=common_row[2],
            avg_duration=common_row[3],
            max_duration=common_row[4],
            stdev_duration=common_row[5],
        )

    def _append_soft_stats_result_table_row(self, irq_nr, irq_stats,
                                            soft_stats_table):
        common_row = self._get_common_stats_result_table_row(False, irq_nr,
                                                             irq_stats)

        if irq_stats.raise_count == 0:
            min_latency = mi.Unknown()
            avg_latency = mi.Unknown()
            max_latency = mi.Unknown()
            stdev_latency = mi.Unknown()
        else:
            min_latency = mi.Duration(irq_stats.min_raise_latency)
            avg_latency = irq_stats.total_raise_latency / irq_stats.raise_count
            avg_latency = mi.Duration(avg_latency)
            max_latency = mi.Duration(irq_stats.max_raise_latency)
            stdev = self._compute_raise_latency_stdev(irq_stats)

            if math.isnan(stdev):
                stdev_latency = mi.Unknown()
            else:
                stdev_latency = mi.Duration(stdev)

        soft_stats_table.append_row(
            irq=common_row[0],
            count=common_row[1],
            min_duration=common_row[2],
            avg_duration=common_row[3],
            max_duration=common_row[4],
            stdev_duration=common_row[5],
            raise_count=mi.Number(irq_stats.raise_count),
            min_latency=min_latency,
            avg_latency=avg_latency,
            max_latency=max_latency,
            stdev_latency=stdev_latency,
        )

    def _fill_freq_result_table(self, irq_stats, freq_table):
        # The number of bins for the histogram
        resolution = self._args.freq_resolution
        if self._args.min is not None:
            min_duration = self._args.min
        else:
            min_duration = irq_stats.min_duration
        if self._args.max is not None:
            max_duration = self._args.max
        else:
            max_duration = irq_stats.max_duration

        # ns to µs
        min_duration /= 1000
        max_duration /= 1000

        # histogram's step
        if self._args.freq_uniform:
            # TODO: perform only one time
            durations = [irq.duration for irq in self._analysis.irq_list]
            min_duration, max_duration, step = \
                self._get_uniform_freq_values(durations)
        else:
            step = (max_duration - min_duration) / resolution

        if step == 0:
            return

        buckets = []
        counts = []

        for i in range(resolution):
            buckets.append(i * step)
            counts.append(0)

        for irq in irq_stats.irq_list:
            duration = irq.duration / 1000
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

    def _fill_stats_freq_result_tables(self, begin_ns, end_ns, is_hard,
                                       analysis_stats, filter_list,
                                       hard_stats_table, soft_stats_table,
                                       freq_tables):
        for id in sorted(analysis_stats):
            if filter_list and str(id) not in filter_list:
                continue

            irq_stats = analysis_stats[id]

            if irq_stats.count == 0:
                continue

            if self._args.stats:
                if is_hard:
                    append_row_fn = self._append_hard_stats_result_table_row
                    table = hard_stats_table
                else:
                    append_row_fn = self._append_soft_stats_result_table_row
                    table = soft_stats_table

                append_row_fn(id, irq_stats, table)

            if self._args.freq:
                subtitle = '{} ({})'.format(irq_stats.name, id)
                freq_table = \
                    self._mi_create_result_table(self._MI_TABLE_CLASS_FREQ,
                                                 begin_ns, end_ns, subtitle)
                self._fill_freq_result_table(irq_stats, freq_table)

                # it is possible that the frequency distribution result
                # table is empty; we need to keep it any way because
                # there's a 1-to-1 association between the statistics
                # row indexes (if available) and the frequency table
                # indexes
                freq_tables.append(freq_table)

    def _get_freq_series_table(self, freq_tables):
        if not freq_tables:
            return

        column_infos = [
            ('duration_lower', 'Duration (lower bound)', mi.Duration),
            ('duration_upper', 'Duration (upper bound)', mi.Duration),
        ]

        for index, freq_table in enumerate(freq_tables):
            column_infos.append((
                'irq{}'.format(index),
                freq_table.subtitle,
                mi.Number,
                'interrupts'
            ))

        title = 'Interrupt handlers duration frequency distributions'
        table_class = mi.TableClass(None, title, column_infos)
        begin = freq_tables[0].timerange.begin.value
        end = freq_tables[0].timerange.end.value
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

    def _get_stats_freq_result_tables(self, begin_ns, end_ns):
        def fill_stats_freq_result_tables(is_hard, stats, filter_list):
            self._fill_stats_freq_result_tables(begin_ns, end_ns, is_hard,
                                                stats, filter_list,
                                                hard_stats_table,
                                                soft_stats_table, freq_tables)

        hard_stats_table = \
            self._mi_create_result_table(self._MI_TABLE_CLASS_HARD_STATS,
                                         begin_ns, end_ns)
        soft_stats_table = \
            self._mi_create_result_table(self._MI_TABLE_CLASS_SOFT_STATS,
                                         begin_ns, end_ns)
        freq_tables = []

        if self._args.irq_filter_list is not None or \
           self._args.softirq_filter_list is None:
            fill_stats_freq_result_tables(True, self._analysis.hard_irq_stats,
                                          self._args.irq_filter_list)

        if self._args.softirq_filter_list is not None or \
           self._args.irq_filter_list is None:
            fill_stats_freq_result_tables(False, self._analysis.softirq_stats,
                                          self._args.softirq_filter_list)

        return hard_stats_table, soft_stats_table, freq_tables

    def _print_log(self, result_table):
        fmt = '[{:<18}, {:<18}] {:>15} {:>4}  {:<9} {:>4}  {:<22}'
        title_fmt = '{:<20} {:<19} {:>15} {:>4}  {:<9} {:>4}  {:<22}'
        print(title_fmt.format('Begin', 'End', 'Duration (us)', 'CPU',
                               'Type', '#', 'Name'))
        for row in result_table.rows:
            timerange = row.time_range
            begin_ts = timerange.begin.value
            end_ts = timerange.end.value

            if type(row.raised_ts) is mi.Timestamp:
                raised_ts = ' (raised at {})'.format(
                    self._format_timestamp(row.raised_ts.value)
                )
            else:
                raised_ts = ''

            cpu_id = row.cpu.id
            irq_do = row.irq

            if irq_do.is_hard:
                irqtype = 'IRQ'
            else:
                irqtype = 'SoftIRQ'

            print(fmt.format(self._format_timestamp(begin_ts),
                             self._format_timestamp(end_ts),
                             '%0.03f' % ((end_ts - begin_ts) / 1000),
                             '%d' % cpu_id, irqtype, irq_do.nr,
                             irq_do.name + raised_ts))

    def _validate_transform_args(self, args):
        args.irq_filter_list = None
        args.softirq_filter_list = None

        if args.irq:
            args.irq_filter_list = args.irq.split(',')
        if args.softirq:
            args.softirq_filter_list = args.softirq.split(',')

    def _compute_duration_stdev(self, irq_stats_item):
        if irq_stats_item.count < 2:
            return float('nan')

        durations = []
        for irq in irq_stats_item.irq_list:
            durations.append(irq.end_ts - irq.begin_ts)

        return statistics.stdev(durations)

    def _compute_raise_latency_stdev(self, irq_stats_item):
        if irq_stats_item.raise_count < 2:
            return float('nan')

        raise_latencies = []
        for irq in irq_stats_item.irq_list:
            if irq.raise_ts is None:
                continue

            raise_latencies.append(irq.begin_ts - irq.raise_ts)

        return statistics.stdev(raise_latencies)

    def _print_frequency_distribution(self, freq_table):
        title_fmt = 'Handler duration frequency distribution {}'

        graph = termgraph.FreqGraph(
            data=freq_table.rows,
            get_value=lambda row: row.count.value,
            get_lower_bound=lambda row: row.duration_lower.to_us(),
            title=title_fmt.format(freq_table.subtitle),
            unit='µs'
        )

        graph.print_graph()

    def _filter_irq(self, irq):
        if type(irq) is sv.HardIRQ:
            if self._args.irq_filter_list:
                return str(irq.id) in self._args.irq_filter_list
            if self._args.softirq_filter_list:
                return False
        else:  # SoftIRQ
            if self._args.softirq_filter_list:
                return str(irq.id) in self._args.softirq_filter_list
            if self._args.irq_filter_list:
                return False

        return True

    def _print_hard_irq_stats_row(self, row):
        output_str = self._get_duration_stats_str(row)
        print(output_str)

    def _print_soft_irq_stats_row(self, row):
        output_str = self._get_duration_stats_str(row)

        if row.raise_count.value != 0:
            output_str += self._get_raise_latency_str(row)

        print(output_str)

    def _get_duration_stats_str(self, row):
        format_str = '{:<3} {:<18} {:>5} {:>12} {:>12} {:>12} {:>12} {:<2}'
        irq_do = row.irq
        count = row.count.value
        min_duration = row.min_duration.to_us()
        avg_duration = row.avg_duration.to_us()
        max_duration = row.max_duration.to_us()

        if type(row.stdev_duration) is mi.Unknown:
            duration_stdev_str = '?'
        else:
            duration_stdev_str = '%0.03f' % row.stdev_duration.to_us()

        output_str = format_str.format('%d:' % irq_do.nr,
                                       '<%s>' % irq_do.name,
                                       '%d' % count,
                                       '%0.03f' % min_duration,
                                       '%0.03f' % avg_duration,
                                       '%0.03f' % max_duration,
                                       '%s' % duration_stdev_str,
                                       ' |')
        return output_str

    def _get_raise_latency_str(self, row):
        format_str = ' {:>6} {:>12} {:>12} {:>12} {:>12}'
        raise_count = row.raise_count.value
        min_raise_latency = row.min_latency.to_us()
        avg_raise_latency = row.avg_latency.to_us()
        max_raise_latency = row.max_latency.to_us()

        if type(row.stdev_latency) is mi.Unknown:
            raise_latency_stdev_str = '?'
        else:
            raise_latency_stdev_str = '%0.03f' % row.stdev_latency.to_us()

        output_str = format_str.format(raise_count,
                                       '%0.03f' % min_raise_latency,
                                       '%0.03f' % avg_raise_latency,
                                       '%0.03f' % max_raise_latency,
                                       '%s' % raise_latency_stdev_str)

        return output_str

    def _print_stats_freq(self, hard_stats_table, soft_stats_table,
                          freq_tables):
        hard_header_format = '{:<52} {:<12}\n' \
                             '{:<22} {:<14} {:<12} {:<12} {:<10} {:<12}\n'
        hard_header = hard_header_format.format(
            'Hard IRQ', 'Duration (us)',
            '', 'count', 'min', 'avg', 'max', 'stdev'
        )
        hard_header += ('-' * 82 + '|')
        soft_header_format = '{:<52} {:<52} {:<12}\n' \
                             '{:<22} {:<14} {:<12} {:<12} {:<10} {:<4} ' \
                             '{:<3} {:<14} {:<12} {:<12} {:<10} {:<12}\n'
        soft_header = soft_header_format.format(
            'Soft IRQ', 'Duration (us)',
            'Raise latency (us)', '',
            'count', 'min', 'avg', 'max', 'stdev', ' |',
            'count', 'min', 'avg', 'max', 'stdev'
        )
        soft_header += '-' * 82 + '|' + '-' * 60

        if hard_stats_table.rows or soft_stats_table.rows:
            stats_rows = itertools.chain(hard_stats_table.rows,
                                         soft_stats_table.rows)

            if freq_tables:
                for stats_row, freq_table in zip(stats_rows, freq_tables):
                    irq = stats_row.irq

                    if irq.is_hard:
                        print(hard_header)
                        self._print_hard_irq_stats_row(stats_row)
                    else:
                        print(soft_header)
                        self._print_soft_irq_stats_row(stats_row)

                    # frequency table might be empty: do not print
                    if freq_table.rows:
                        print()
                        self._print_frequency_distribution(freq_table)

                    print()

            else:
                hard_header_printed = False
                soft_header_printed = False

                for stats_row in stats_rows:
                    irq = stats_row.irq

                    if irq.is_hard:
                        if not hard_header_printed:
                            print(hard_header)
                            hard_header_printed = True

                        self._print_hard_irq_stats_row(stats_row)
                    else:
                        if not soft_header_printed:
                            if hard_header_printed:
                                print()

                            print(soft_header)
                            soft_header_printed = True

                        self._print_soft_irq_stats_row(stats_row)

            return

        for freq_table in freq_tables:
            # frequency table might be empty: do not print
            if freq_table.rows:
                print()
                self._print_frequency_distribution(freq_table)

    def _add_arguments(self, ap):
        Command._add_min_max_args(ap)
        Command._add_freq_args(
            ap, help='Output the frequency distribution of handler durations')
        Command._add_log_args(
            ap, help='Output the IRQs in chronological order')
        Command._add_stats_args(ap, help='Output IRQ statistics')
        ap.add_argument('--irq', type=str, default=None,
                        help='Output results only for the list of IRQ')
        ap.add_argument('--softirq', type=str, default=None,
                        help='Output results only for the list of SoftIRQ')


def _run(mi_mode):
    irqcmd = IrqAnalysisCommand(mi_mode=mi_mode)
    irqcmd.run()


def _runstats(mi_mode):
    sys.argv.insert(1, '--stats')
    _run(mi_mode)


def _runlog(mi_mode):
    sys.argv.insert(1, '--log')
    _run(mi_mode)


def _runfreq(mi_mode):
    sys.argv.insert(1, '--freq')
    _run(mi_mode)


def runstats():
    _runstats(mi_mode=False)


def runlog():
    _runlog(mi_mode=False)


def runfreq():
    _runfreq(mi_mode=False)


def runstats_mi():
    _runstats(mi_mode=True)


def runlog_mi():
    _runlog(mi_mode=True)


def runfreq_mi():
    _runfreq(mi_mode=True)
