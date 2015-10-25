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
from ..core import irq as core_irq
from ..linuxautomaton import common, sv
from ..ascii_graph import Pyasciigraph

import math
import statistics
import sys


class IrqAnalysisCommand(Command):
    _DESC = """The irq command."""
    _ANALYSIS_CLASS = core_irq.IrqAnalysis

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

    def _print_frequency_distribution(self, irq_stats_item, id):
        # The number of bins for the histogram
        resolution = self._args.freq_resolution

        min_duration = irq_stats_item.min_duration
        max_duration = irq_stats_item.max_duration
        # ns to µs
        min_duration /= 1000
        max_duration /= 1000

        step = (max_duration - min_duration) / resolution
        if step == 0:
            return

        buckets = []
        values = []
        graph = Pyasciigraph()
        for i in range(resolution):
            buckets.append(i * step)
            values.append(0)
        for irq in irq_stats_item.irq_list:
            duration = (irq.end_ts - irq.begin_ts) / 1000
            index = min(int((duration - min_duration) / step), resolution - 1)
            values[index] += 1

        graph_data = []
        for index, value in enumerate(values):
            # The graph data format is a tuple (info, value). Here info
            # is the lower bound of the bucket, value the bucket's count
            graph_data.append(('%0.03f' % (index * step + min_duration),
                               value))

        graph_lines = graph.graph(
            'Handler duration frequency distribution %s (%s) (usec)' %
            (irq_stats_item.name, id),
            graph_data,
            info_before=True,
            count=True
        )

        for line in graph_lines:
            print(line)

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

    def _print_irq_log(self):
        fmt = '[{:<18}, {:<18}] {:>15} {:>4}  {:<9} {:>4}  {:<22}'
        title_fmt = '{:<20} {:<19} {:>15} {:>4}  {:<9} {:>4}  {:<22}'
        print(title_fmt.format('Begin', 'End', 'Duration (us)', 'CPU',
                               'Type', '#', 'Name'))
        for irq in self._analysis.irq_list:
            if not self._filter_irq(irq):
                continue

            raise_ts = ''
            if type(irq) is sv.HardIRQ:
                name = self._analysis.hard_irq_stats[irq.id].name
                irqtype = 'IRQ'
            else:
                name = self._analysis.softirq_stats[irq.id].name
                irqtype = 'SoftIRQ'
                if irq.raise_ts is not None:
                    raise_ts = ' (raised at %s)' % \
                               (common.ns_to_hour_nsec(irq.raise_ts,
                                                       self._args.multi_day,
                                                       self._args.gmt))

            print(fmt.format(common.ns_to_hour_nsec(irq.begin_ts,
                                                    self._args.multi_day,
                                                    self._args.gmt),
                             common.ns_to_hour_nsec(irq.end_ts,
                                                    self._args.multi_day,
                                                    self._args.gmt),
                             '%0.03f' % ((irq.end_ts - irq.begin_ts) / 1000),
                             '%d' % irq.cpu_id, irqtype, irq.id,
                             name + raise_ts))

    def _print_irq_stats(self, irq_stats, filter_list, header):
        header_printed = False
        for id in sorted(irq_stats):
            if filter_list and str(id) not in filter_list:
                continue

            irq_stats_item = irq_stats[id]
            if irq_stats_item.count == 0:
                continue

            if self._args.stats:
                if self._args.freq or not header_printed:
                    print(header)
                    header_printed = True

                if type(irq_stats_item) is core_irq.HardIrqStats:
                    self._print_hard_irq_stats_item(irq_stats_item, id)
                else:
                    self._print_soft_irq_stats_item(irq_stats_item, id)

            if self._args.freq:
                self._print_frequency_distribution(irq_stats_item, id)

        print()

    def _print_hard_irq_stats_item(self, irq_stats_item, id):
        output_str = self._get_duration_stats_str(irq_stats_item, id)
        print(output_str)

    def _print_soft_irq_stats_item(self, irq_stats_item, id):
        output_str = self._get_duration_stats_str(irq_stats_item, id)
        if irq_stats_item.raise_count != 0:
            output_str += self._get_raise_latency_str(irq_stats_item, id)

        print(output_str)

    def _get_duration_stats_str(self, irq_stats_item, id):
        format_str = '{:<3} {:<18} {:>5} {:>12} {:>12} {:>12} {:>12} {:<2}'

        avg_duration = irq_stats_item.total_duration / irq_stats_item.count
        duration_stdev = self._compute_duration_stdev(irq_stats_item)
        min_duration = irq_stats_item.min_duration
        max_duration = irq_stats_item.max_duration
        # ns to µs
        avg_duration /= 1000
        duration_stdev /= 1000
        min_duration /= 1000
        max_duration /= 1000

        if math.isnan(duration_stdev):
            duration_stdev_str = '?'
        else:
            duration_stdev_str = '%0.03f' % duration_stdev

        output_str = format_str.format('%d:' % id,
                                       '<%s>' % irq_stats_item.name,
                                       '%d' % irq_stats_item.count,
                                       '%0.03f' % min_duration,
                                       '%0.03f' % avg_duration,
                                       '%0.03f' % max_duration,
                                       '%s' % duration_stdev_str,
                                       ' |')
        return output_str

    def _get_raise_latency_str(self, irq_stats_item, id):
        format_str = ' {:>6} {:>12} {:>12} {:>12} {:>12}'

        avg_raise_latency = (irq_stats_item.total_raise_latency /
                             irq_stats_item.raise_count)
        raise_latency_stdev = self._compute_raise_latency_stdev(irq_stats_item)
        min_raise_latency = irq_stats_item.min_raise_latency
        max_raise_latency = irq_stats_item.max_raise_latency
        # ns to µs
        avg_raise_latency /= 1000
        raise_latency_stdev /= 1000
        min_raise_latency /= 1000
        max_raise_latency /= 1000

        if math.isnan(raise_latency_stdev):
            raise_latency_stdev_str = '?'
        else:
            raise_latency_stdev_str = '%0.03f' % raise_latency_stdev

        output_str = format_str.format(irq_stats_item.raise_count,
                                       '%0.03f' % min_raise_latency,
                                       '%0.03f' % avg_raise_latency,
                                       '%0.03f' % max_raise_latency,
                                       '%s' % raise_latency_stdev_str)
        return output_str

    def _print_results(self, begin_ns, end_ns):
        if self._args.stats or self._args.freq:
            self._print_stats(begin_ns, end_ns)
        if self._args.log:
            self._print_irq_log()

    def _print_stats(self, begin_ns, end_ns):
        self._print_date(begin_ns, end_ns)

        if self._args.irq_filter_list is not None or \
           self._args.softirq_filter_list is None:
            header_format = '{:<52} {:<12}\n' \
                            '{:<22} {:<14} {:<12} {:<12} {:<10} {:<12}\n'
            header = header_format.format(
                'Hard IRQ', 'Duration (us)',
                '', 'count', 'min', 'avg', 'max', 'stdev'
            )
            header += ('-' * 82 + '|')
            self._print_irq_stats(self._analysis.hard_irq_stats,
                                  self._args.irq_filter_list,
                                  header)

        if self._args.softirq_filter_list is not None or \
           self._args.irq_filter_list is None:
            header_format = '{:<52} {:<52} {:<12}\n' \
                            '{:<22} {:<14} {:<12} {:<12} {:<10} {:<4} ' \
                            '{:<3} {:<14} {:<12} {:<12} {:<10} {:<12}\n'
            header = header_format.format(
                'Soft IRQ', 'Duration (us)',
                'Raise latency (us)', '',
                'count', 'min', 'avg', 'max', 'stdev', ' |',
                'count', 'min', 'avg', 'max', 'stdev'
            )
            header += '-' * 82 + '|' + '-' * 60
            self._print_irq_stats(self._analysis.softirq_stats,
                                  self._args.softirq_filter_list,
                                  header)

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


# entry point
def runstats():
    sys.argv.insert(1, '--stats')
    irqcmd = IrqAnalysisCommand()
    irqcmd.run()


def runlog():
    sys.argv.insert(1, '--log')
    irqcmd = IrqAnalysisCommand()
    irqcmd.run()


def runfreq():
    sys.argv.insert(1, '--freq')
    irqcmd = IrqAnalysisCommand()
    irqcmd.run()
