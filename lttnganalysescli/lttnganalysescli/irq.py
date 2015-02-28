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
import lttnganalyses.irq
from linuxautomaton import common, sv
from ascii_graph import Pyasciigraph
import statistics


class IrqAnalysis(Command):
    _VERSION = '0.1.0'
    _DESC = """The irq command."""

    def __init__(self):
        super().__init__(self._add_arguments,
                         enable_max_min_args=True,
                         enable_freq_arg=True,
                         enable_log_arg=True,
                         enable_stats_arg=True)

    def _validate_transform_args(self):
        # We need the min/max in the automaton to filter
        # at the source.
        self.state.max = self._arg_max
        self.state.min = self._arg_min

        self._arg_irq_filter_list = None
        self._arg_softirq_filter_list = None
        if self._args.irq:
            self._arg_irq_filter_list = self._args.irq.split(",")
        if self._args.softirq:
            self._arg_softirq_filter_list = self._args.softirq.split(",")
        if self._arg_irq_filter_list is None and \
                self._arg_softirq_filter_list is None:
            self._arg_irq_filter_list = []
            self._arg_softirq_filter_list = []

    def _default_args(self, stats, log, freq):
        if stats:
            self._arg_stats = True
        if log:
            self._arg_log = True
        if freq:
            self._arg_freq = True

    def run(self, stats=False, log=False, freq=False):
        # parse arguments first
        self._parse_args()
        # validate, transform and save specific arguments
        self._validate_transform_args()
        # handle the default args for different executables
        self._default_args(stats, log, freq)
        # open the trace
        self._open_trace()
        # create the appropriate analysis/analyses
        self._create_analysis()
        # run the analysis
        self._run_analysis(self._reset_total, self._refresh)
        # process the results
        self._compute_stats()
        # print results
        self._print_results(self.start_ns, self.trace_end_ts, final=1)
        # close the trace
        self._close_trace()

    def run_stats(self):
        self.run(stats=True)

    def run_log(self):
        self.run(log=True)

    def run_freq(self):
        self.run(freq=True)

    def _create_analysis(self):
        self._analysis = lttnganalyses.irq.IrqAnalysis(self.state)

    def compute_stdev(self, irq):
        values = []
        raise_delays = []
        stdev = {}
        for j in irq["list"]:
            delay = j.stop_ts - j.start_ts
            values.append(delay)
            if j.raise_ts is None:
                continue
            # Raise latency (only for some softirqs)
            r_d = j.start_ts - j.raise_ts
            raise_delays.append(r_d)
        if irq["count"] < 2:
            stdev["duration"] = "?"
        else:
            stdev["duration"] = "%0.03f" % (statistics.stdev(values) / 1000)
        # format string for the raise if present
        if irq["raise_count"] >= 2:
            stdev["raise"] = "%0.03f" % (statistics.stdev(raise_delays)/1000)
        return stdev

    def irq_list_to_freq(self, irq, _min, _max, res, name, nr):
        step = (_max - _min) / res
        if step == 0:
            return
        buckets = []
        values = []
        graph = Pyasciigraph()
        for i in range(res):
            buckets.append(i * step)
            values.append(0)
        for i in irq["list"]:
            v = (i.stop_ts - i.start_ts) / 1000
            b = min(int((v-_min)/step), res - 1)
            values[b] += 1
        g = []
        i = 0
        for v in values:
            g.append(("%0.03f" % (i * step + _min), v))
            i += 1
        for line in graph.graph('Handler duration frequency distribution %s '
                                '(%s) (usec)' % (name, nr),
                                g, info_before=True, count=True):
            print(line)
        print("")

    # FIXME: there must be a way to make that more complicated/ugly
    def filter_irq(self, i):
        if i.irqclass == sv.IRQ.HARD_IRQ:
            if self._arg_irq_filter_list is not None:
                if len(self._arg_irq_filter_list) > 0 and \
                        str(i.nr) not in self._arg_irq_filter_list:
                    return False
                else:
                    return True
            if self._arg_softirq_filter_list is not None and \
                    len(self._arg_softirq_filter_list) > 0:
                return False
        else:
            if self._arg_softirq_filter_list is not None:
                if len(self._arg_softirq_filter_list) > 0 and \
                        str(i.nr) not in self._arg_softirq_filter_list:
                    return False
                else:
                    return True
            if self._arg_irq_filter_list is not None and \
                    len(self._arg_irq_filter_list) > 0:
                return False
        raise Exception("WTF")

    def log_irq(self):
        fmt = "[{:<18}, {:<18}] {:>15} {:>4}  {:<9} {:>4}  {:<22}"
        title_fmt = "{:<20} {:<19} {:>15} {:>4}  {:<9} {:>4}  {:<22}"
        print(title_fmt.format("Begin", "End", "Duration (us)", "CPU",
                               "Type", "#", "Name"))
        for i in self.state.interrupts["irq-list"]:
            if not self.filter_irq(i):
                continue
            if i.irqclass == sv.IRQ.HARD_IRQ:
                name = self.state.interrupts["names"][i.nr]
                irqtype = "IRQ"
            else:
                name = sv.IRQ.soft_names[i.nr]
                irqtype = "SoftIRQ"
            if i.raise_ts is not None:
                raise_ts = " (raised at %s)" % \
                           (common.ns_to_hour_nsec(i.raise_ts,
                                                   self._arg_multi_day,
                                                   self._arg_gmt))
            else:
                raise_ts = ""
            print(fmt.format(common.ns_to_hour_nsec(i.start_ts,
                                                    self._arg_multi_day,
                                                    self._arg_gmt),
                             common.ns_to_hour_nsec(i.stop_ts,
                                                    self._arg_multi_day,
                                                    self._arg_gmt),
                             "%0.03f" % ((i.stop_ts - i.start_ts) / 1000),
                             "%d" % i.cpu_id, irqtype, i.nr, name + raise_ts))

    def print_irq_stats(self, dic, name_table, filter_list, header):
        header_output = 0
        for i in sorted(dic.keys()):
            if len(filter_list) > 0 and str(i) not in filter_list:
                continue
            name = name_table[i]
            stdev = self.compute_stdev(dic[i])

            # format string for the raise if present
            if dic[i]["raise_count"] < 2:
                raise_stats = " |"
            else:
                r_avg = dic[i]["raise_total"] / (dic[i]["raise_count"] * 1000)
                raise_stats = " | {:>6} {:>12} {:>12} {:>12} {:>12}".format(
                    dic[i]["raise_count"],
                    "%0.03f" % (dic[i]["raise_min"] / 1000),
                    "%0.03f" % r_avg,
                    "%0.03f" % (dic[i]["raise_max"] / 1000),
                    stdev["raise"])

            # final output
            if dic[i]["count"] == 0:
                continue
            avg = "%0.03f" % (dic[i]["total"] / (dic[i]["count"] * 1000))
            format_str = '{:<3} {:<18} {:>5} {:>12} {:>12} {:>12} ' \
                         '{:>12} {:<60}'
            s = format_str.format("%d:" % i, "<%s>" % name, dic[i]["count"],
                                  "%0.03f" % (dic[i]["min"] / 1000),
                                  "%s" % (avg),
                                  "%0.03f" % (dic[i]["max"] / 1000),
                                  "%s" % (stdev["duration"]),
                                  raise_stats)
            if self._arg_stats and (self._arg_freq or header_output == 0):
                print(header)
                header_output = 1
            if self._arg_stats:
                print(s)
            if self._arg_freq:
                self.irq_list_to_freq(dic[i], dic[i]["min"] / 1000,
                                      dic[i]["max"] / 1000,
                                      self._arg_freq_resolution, name, str(i))

    def _print_results(self, begin_ns, end_ns, final=0):
        if self._arg_stats or self._arg_freq:
            self._print_stats(begin_ns, end_ns, final)
        if self._arg_log:
            self.log_irq()

    def _print_stats(self, begin_ns, end_ns, final):
        if self._arg_no_progress:
            clear_screen = ""
        else:
            clear_screen = "\r" + self.pbar.term_width * " " + "\r"
        date = 'Timerange: [%s, %s]' % (
            common.ns_to_hour_nsec(begin_ns, gmt=self._arg_gmt,
                                   multi_day=True),
            common.ns_to_hour_nsec(end_ns, gmt=self._arg_gmt,
                                   multi_day=True))
        print(clear_screen + date)
        if self._arg_irq_filter_list is not None:
            header = ""
            header += '{:<52} {:<12}\n'.format("Hard IRQ", "Duration (us)")
            header += '{:<22} {:<14} {:<12} {:<12} {:<10} ' \
                      '{:<12}\n'.format("", "count", "min", "avg", "max",
                                        "stdev")
            header += ('-'*82 + "|")
            self.print_irq_stats(self.state.interrupts["hard-irqs"],
                                 self.state.interrupts["names"],
                                 self._arg_irq_filter_list, header)
            print("")

        if self._arg_softirq_filter_list is not None:
            header = ""
            header += '{:<52} {:<52} {:<12}\n'.format("Soft IRQ",
                                                      "Duration (us)",
                                                      "Raise latency (us)")
            header += '{:<22} {:<14} {:<12} {:<12} {:<10} {:<4} {:<3} {:<14} '\
                      '{:<12} {:<12} {:<10} ' \
                      '{:<12}\n'.format("", "count", "min", "avg", "max",
                                        "stdev", " |", "count", "min",
                                        "avg", "max", "stdev")
            header += '-' * 82 + "|" + '-' * 60
            self.print_irq_stats(self.state.interrupts["soft-irqs"],
                                 sv.IRQ.soft_names,
                                 self._arg_softirq_filter_list,
                                 header)
            print("")

    def _compute_stats(self):
        pass

    def _reset_total(self, start_ts):
        self.state.interrupts["hard_count"] = 0
        self.state.interrupts["soft_count"] = 0
        self.state.interrupts["irq-list"] = []
        for i in self.state.interrupts["hard-irqs"].keys():
            self.state.interrupts["hard-irqs"][i] = sv.IRQ.init_irq_instance()
        for i in self.state.interrupts["soft-irqs"].keys():
            self.state.interrupts["soft-irqs"][i] = sv.IRQ.init_irq_instance()

    def _refresh(self, begin, end):
        self._compute_stats()
        self._print_results(begin, end, final=0)
        self._reset_total(end)

    def _add_arguments(self, ap):
        ap.add_argument('--irq', type=str, default=0,
                        help='Show results only for the list of IRQ')
        ap.add_argument('--softirq', type=str, default=0,
                        help='Show results only for the list of '
                             'SoftIRQ')


# entry point
def runstats():
    # create command
    irqcmd = IrqAnalysis()
    # execute command
    irqcmd.run_stats()


def runlog():
    # create command
    irqcmd = IrqAnalysis()
    # execute command
    irqcmd.run_log()


def runfreq():
    # create command
    irqcmd = IrqAnalysis()
    # execute command
    irqcmd.run_freq()
