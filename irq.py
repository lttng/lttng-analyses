#!/usr/bin/env python3
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

import argparse
import sys
import statistics

try:
    from babeltrace import TraceCollection
except ImportError:
    # quick fix for debian-based distros
    sys.path.append("/usr/local/lib/python%d.%d/site-packages" %
                    (sys.version_info.major, sys.version_info.minor))
    from babeltrace import TraceCollection
from LTTngAnalyzes.common import NSEC_PER_SEC, ns_to_asctime, IRQ
from LTTngAnalyzes.progressbar import progressbar_setup, progressbar_update, \
    progressbar_finish
from LTTngAnalyzes.state import State
from ascii_graph import Pyasciigraph


class IrqStats():
    def __init__(self, traces):
        self.trace_start_ts = 0
        self.trace_end_ts = 0
        self.traces = traces
        self.state = State()

    def run(self, args):
        """Process the trace"""
        self.current_sec = 0
        self.start_ns = 0
        self.end_ns = 0

        progressbar_setup(self, args)
        for event in self.traces.events:
            progressbar_update(self, args)
            if self.start_ns == 0:
                self.start_ns = event.timestamp
            if self.trace_start_ts == 0:
                self.trace_start_ts = event.timestamp
            self.end_ns = event.timestamp
            self.check_refresh(args, event)
            self.trace_end_ts = event.timestamp

            if event.name == "sched_switch":
                self.state.sched.switch(event)
            elif event.name == "irq_handler_entry":
                self.state.irq.hard_entry(event)
            elif event.name == "irq_handler_exit":
                self.state.irq.hard_exit(event, args)
            elif event.name == "softirq_entry":
                self.state.irq.soft_entry(event)
            elif event.name == "softirq_exit":
                self.state.irq.soft_exit(event, args)
            elif event.name == "softirq_raise":
                self.state.irq.soft_raise(event)
        if args.refresh == 0:
            # stats for the whole trace
            self.output(args, self.trace_start_ts, self.trace_end_ts, final=1)
        else:
            # stats only for the last segment
            self.output(args, self.start_ns, self.trace_end_ts, final=1)
        progressbar_finish(self, args)

    def check_refresh(self, args, event):
        """Check if we need to output something"""
        if args.refresh == 0:
            return
        event_sec = event.timestamp / NSEC_PER_SEC
        if self.current_sec == 0:
            self.current_sec = event_sec
        elif self.current_sec != event_sec and \
                (self.current_sec + args.refresh) <= event_sec:
            self.output(args, self.start_ns, event.timestamp)
            self.reset_total(event.timestamp)
            self.current_sec = event_sec
            self.start_ns = event.timestamp

    def compute_stdev(self, irq):
        values = []
        raise_delays = []
        stdev = {}
        for j in irq["list"]:
            delay = j.stop_ts - j.start_ts
            values.append(delay)
            if j.raise_ts == -1:
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

    def irq_list_to_freq(self, irq, _min, _max, res):
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
        for line in graph.graph('freq', g):
            print(line)
        print("")

    def print_irq_stats(self, args, dic, name_table, filter_list, header):
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
            if args.freq or header_output == 0:
                print(header)
                header_output = 1
            print(s)
            if args.freq:
                self.irq_list_to_freq(dic[i], dic[i]["min"] / 1000,
                                      dic[i]["max"] / 1000,
                                      args.freq_resolution)

    def output(self, args, begin_ns, end_ns, final=0):
        if args.no_progress:
            clear_screen = ""
        else:
            clear_screen = "\r" + self.pbar.term_width * " " + "\r"
        date = '%s to %s' % (ns_to_asctime(begin_ns), ns_to_asctime(end_ns))
        print(clear_screen + date)
        if args.irq_filter_list is not None:
            header = ""
            header += '{:<52} {:<12}\n'.format("Hard IRQ", "Duration (us)")
            header += '{:<22} {:<14} {:<12} {:<12} {:<10} ' \
                      '{:<12}\n'.format("", "count", "min", "avg", "max",
                                        "stdev")
            header += ('-'*82 + "|")
            self.print_irq_stats(args, self.state.interrupts["hard-irqs"],
                                 self.state.interrupts["names"],
                                 args.irq_filter_list, header)
            print("")

        if args.softirq_filter_list is not None:
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
            self.print_irq_stats(args, self.state.interrupts["soft-irqs"],
                                 IRQ.soft_names, args.softirq_filter_list,
                                 header)
            print("")

    def reset_total(self, start_ts):
        self.state.interrupts["hard_count"] = 0
        self.state.interrupts["soft_count"] = 0
        for i in self.state.interrupts["hard-irqs"].keys():
            self.state.interrupts["hard-irqs"][i] = self.state.irq.init_irq()
        for i in self.state.interrupts["soft-irqs"].keys():
            self.state.interrupts["soft-irqs"][i] = self.state.irq.init_irq()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Memory usage analysis')
    parser.add_argument('path', metavar="<path/to/trace>", help='Trace path')
    parser.add_argument('-r', '--refresh', type=int,
                        help='Refresh period in seconds', default=0)
    parser.add_argument('--top', type=int, default=10,
                        help='Limit to top X TIDs (default = 10)')
    parser.add_argument('--no-progress', action="store_true",
                        help='Don\'t display the progress bar')
    parser.add_argument('--details', action="store_true",
                        help='Display all the IRQs details')
    parser.add_argument('--thresh', type=int, default=0,
                        help='Threshold in ns for the detailled view')
    parser.add_argument('--irq', type=str, default=0,
                        help='Show results only for the list of IRQ')
    parser.add_argument('--softirq', type=str, default=0,
                        help='Show results only for the list of SoftIRQ')
    parser.add_argument('--freq', action="store_true",
                        help='Show the frequency distribution of handler '
                             'duration')
    parser.add_argument('--freq-resolution', type=int, default=20,
                        help='Frequency distribution resolution (default 20)')
    parser.add_argument('--max', type=float, default=-1,
                        help='Filter out, duration longer than max usec')
    parser.add_argument('--min', type=float, default=-1,
                        help='Filter out, duration shorter than min usec')
    args = parser.parse_args()

    args.irq_filter_list = None
    args.softirq_filter_list = None

    if args.irq:
        args.irq_filter_list = args.irq.split(",")

    if args.softirq:
        args.softirq_filter_list = args.softirq.split(",")
    if args.irq_filter_list is None and args.softirq_filter_list is None:
        args.irq_filter_list = []
        args.softirq_filter_list = []
    if args.max == -1:
        args.max = None
    if args.min == -1:
        args.min = None

    traces = TraceCollection()
    handle = traces.add_traces_recursive(args.path, "ctf")
    if handle is None:
        sys.exit(1)

    c = IrqStats(traces)

    c.run(args)

    for h in handle.values():
        traces.remove_trace(h)
