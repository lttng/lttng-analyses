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
            elif event.name == "softirq_raise":
                irq.soft_raise(event)
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
            count = maxtime = total = 0
            mintime = -1
            values = []
            v = []
            r_count = r_maxtime = r_total = 0
            r_mintime = -1
            raise_delays = []
            r = []
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
                if j.raise_ts == -1:
                    continue

                r_count += 1
                r_d = j.start_ts - j.raise_ts
                r_total += r_d
                if r_d > r_maxtime:
                    r_maxtime = r_d
                    if r_mintime == -1:
                        r_mintime = r_maxtime
                if r_d < r_mintime:
                    r_mintime = r_d
                raise_delays.append(r_d)
                r.append(("%s to %s" % (ns_to_hour_nsec(j.raise_ts),
                          ns_to_hour_nsec(j.start_ts)), r_d))
            if count == 0:
                continue
            elif count < 2:
                stdev = "?"
            else:
                stdev = statistics.stdev(values)

            if r_count < 2:
                r_stdev = ""
            else:
                st = statistics.stdev(raise_delays)
                r_avg = r_total / r_count
                r_stdev = "\n\traised %d times\n\tdelay before handler_entry" \
                          " (ns):\n\t\tmin = %d\n\t\tmax = %d\n\t\tavg = %d" \
                          "\n\t\tstdev = %s" % \
                          (r_count, r_mintime, r_maxtime, r_avg, st)

            print("- IRQ %d (%s):\n\t %d interrupts\n\t delay (ns):"
                  "\n\t\t min = %d\n\t\t max = %d\n\t\t avg = %d"
                  "\n\t\t stdev = %s%s" %
                  (i, name, count, mintime, maxtime, total/count,
                   stdev, r_stdev))
            if not args.details:
                continue
            for line in graph.graph("IRQs delay repartition", v,
                                    unit=" ns"):
                print(line)

    def output(self, args, begin_ns, end_ns, final=0):
        print('%s to %s' % (ns_to_asctime(begin_ns), ns_to_asctime(end_ns)))
        print("\nHard IRQs (%d):" % self.irq["hard_count"])
        self.print_irq_stats(args, self.irq["hard-irqs"], self.irq["names"])

        print("\nSoft IRQs (%d):" % self.irq["soft_count"])
        self.print_irq_stats(args, self.irq["soft-irqs"], IRQ.soft_names)
        print("")

    def reset_total(self, start_ts):
        self.irq["hard_count"] = 0
        self.irq["soft_count"] = 0
        for i in self.irq["hard-irqs"].keys():
            self.irq["hard-irqs"][i] = []
        for i in self.irq["soft-irqs"].keys():
            self.irq["soft-irqs"][i] = []

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
