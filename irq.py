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
from LTTngAnalyzes.common import NSEC_PER_SEC, ns_to_asctime, getFolderSize, \
    BYTES_PER_EVENT, ns_to_hour_nsec, IRQ
from LTTngAnalyzes.sched import Sched
from LTTngAnalyzes.irq import Interrupt
from ascii_graph import Pyasciigraph

try:
    from progressbar import ETA, Bar, Percentage, ProgressBar
    progressbar_available = True
except ImportError:
    progressbar_available = False


class IrqStats():
    def __init__(self, traces):
        self.trace_start_ts = 0
        self.trace_end_ts = 0
        self.traces = traces
        self.tids = {}
        self.cpus = {}
        self.irq = {}
        self.mm = {}

    def run(self, args):
        """Process the trace"""
        self.current_sec = 0
        self.start_ns = 0
        self.end_ns = 0

        if not args.no_progress:
            if progressbar_available:
                size = getFolderSize(args.path)
                widgets = ['Processing the trace: ', Percentage(), ' ',
                           Bar(marker='#', left='[', right=']'),
                           ' ', ETA(), ' ']  # see docs for other options
                pbar = ProgressBar(widgets=widgets,
                                   maxval=size/BYTES_PER_EVENT)
                pbar.start()
            else:
                print("Warning: progressbar module not available, "
                      "using --no-progress.", file=sys.stderr)
                args.no_progress = True

        sched = Sched(self.cpus, self.tids)
        irq = Interrupt(self.irq, self.cpus, self.tids)
        event_count = 0
        for event in self.traces.events:
            if not args.no_progress:
                try:
                    pbar.update(event_count)
                except ValueError:
                    pass
            event_count += 1
            if self.start_ns == 0:
                self.start_ns = event.timestamp
            if self.trace_start_ts == 0:
                self.trace_start_ts = event.timestamp
            self.end_ns = event.timestamp
            self.check_refresh(args, event)
            self.trace_end_ts = event.timestamp

            if event.name == "sched_switch":
                sched.switch(event)
            elif event.name == "irq_handler_entry":
                irq.hard_entry(event)
            elif event.name == "irq_handler_exit":
                irq.hard_exit(event)
            elif event.name == "softirq_entry":
                irq.soft_entry(event)
            elif event.name == "softirq_exit":
                irq.soft_exit(event)
        if not args.no_progress:
            pbar.finish()
            print
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

    def print_irq_stats(self, args, dic, name_table):
        for i in dic.keys():
            name = name_table[i]
            graph = Pyasciigraph()
            count = 0
            maxtime = 0
            mintime = -1
            total = 0
            values = []
            v = []
            for j in dic[i]:
                count += 1
                delay = j.stop_ts - j.start_ts
                if delay > maxtime:
                    maxtime = delay
                    if mintime == -1:
                        mintime = maxtime
                if delay < mintime:
                    mintime = delay
                values.append(delay)
                total += delay
                if delay > args.thresh:
                    v.append(("%s to %s" % (ns_to_hour_nsec(j.start_ts),
                              ns_to_hour_nsec(j.stop_ts)), delay))
            print("- IRQ %d (%s): %d interrupts, delay (ns): min = %d, "
                  "max = %s, avg = %d, stdev = %d" %
                  (i, name, count, mintime, maxtime, total/count,
                   statistics.stdev(values)))
            if not args.details:
                continue
            for line in graph.graph("IRQs delay repartition", v,
                                    unit=" ns"):
                print(line)

    def output(self, args, begin_ns, end_ns, final=0):
        print('%s to %s' % (ns_to_asctime(begin_ns), ns_to_asctime(end_ns)))
        print("Total :\n- %d hard IRQs" % (self.irq["hard_count"]))
        print("- %d soft IRQs" % (self.irq["soft_count"]))

        print("\nHard IRQs:")
        self.print_irq_stats(args, self.irq["hard-irqs"], self.irq["names"])

        print("\nSoft IRQs:")
        self.print_irq_stats(args, self.irq["soft-irqs"], IRQ.soft_names)

    def reset_total(self, start_ts):
        for tid in self.tids.keys():
            self.tids[tid].allocated_pages = 0
            self.tids[tid].freed_pages = 0
        self.mm["allocated_pages"] = 0
        self.mm["freed_pages"] = 0

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
    handle = traces.add_trace(args.path, "ctf")
    if handle is None:
        sys.exit(1)

    c = IrqStats(traces)

    c.run(args)

    traces.remove_trace(handle)
