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
                self.state.irq.hard_exit(event)
            elif event.name == "softirq_entry":
                self.state.irq.soft_entry(event)
            elif event.name == "softirq_exit":
                self.state.irq.soft_exit(event)
            elif event.name == "softirq_raise":
                self.state.irq.soft_raise(event)
        progressbar_finish(self, args)
        if args.refresh == 0:
            # stats for the whole trace
            self.output(args, self.trace_start_ts, self.trace_end_ts, final=1)
        else:
            # stats only for the last segment
            self.output(args, self.start_ns, self.trace_end_ts, final=1)

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

    def print_irq_stats(self, args, dic, name_table):
        for i in sorted(dic.keys()):
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
            avg = "%0.03f" % (dic[i]["total"] / (dic[i]["count"] * 1000))
            format_str = '{:<3} {:<18} {:>5} {:>12} {:>12} {:>12} ' \
                         '{:>12} {:<60}'
            s = format_str.format("%d:" % i, "<%s>" % name, dic[i]["count"],
                                  "%0.03f" % (dic[i]["min"] / 1000),
                                  "%s" % (avg),
                                  "%0.03f" % (dic[i]["max"] / 1000),
                                  "%s" % (stdev["duration"]),
                                  raise_stats)
            print(s)

    def output(self, args, begin_ns, end_ns, final=0):
        print('%s to %s' % (ns_to_asctime(begin_ns), ns_to_asctime(end_ns)))
        print('{:<52} {:<12}'.format("Hard IRQ", "Duration (us)"))
        print('{:<22} {:<14} {:<12} {:<12} {:<10} {:<12}'.format("", "count",
                                                                 "min", "avg",
                                                                 "max",
                                                                 "stdev"))
        print('-'*82 + "|")
        self.print_irq_stats(args, self.state.interrupts["hard-irqs"],
                             self.state.interrupts["names"])

        print("")
        print('{:<52} {:<52} {:<12}'.format("Soft IRQ", "Duration (us)",
                                            "Raise latency (us)"))
        print('{:<22} {:<14} {:<12} {:<12} {:<10} {:<4} {:<3} {:<14} {:<12} '
              '{:<12} {:<10} {:<12}'.format("", "count", "min", "avg", "max",
                                            "stdev", " |", "count", "min",
                                            "avg", "max", "stdev"))
        print('-' * 82 + "|" + '-' * 60)
        self.print_irq_stats(args, self.state.interrupts["soft-irqs"],
                             IRQ.soft_names)
        print("")

    def reset_total(self, start_ts):
        self.state.interrupts["hard_count"] = 0
        self.state.interrupts["soft_count"] = 0
        for i in self.state.interrupts["hard-irqs"].keys():
            self.state.interrupts["hard-irqs"][i] = []
        for i in self.state.interrupts["soft-irqs"].keys():
            self.state.interrupts["soft-irqs"][i] = []

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
    args = parser.parse_args()

    traces = TraceCollection()
    handle = traces.add_traces_recursive(args.path, "ctf")
    if handle is None:
        sys.exit(1)

    c = IrqStats(traces)

    c.run(args)

    for h in handle.values():
        traces.remove_trace(h)
