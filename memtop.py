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
import operator
import sys
try:
    from babeltrace import TraceCollection
except ImportError:
    # quick fix for debian-based distros
    sys.path.append("/usr/local/lib/python%d.%d/site-packages" %
                    (sys.version_info.major, sys.version_info.minor))
    from babeltrace import TraceCollection
from LTTngAnalyzes.common import NSEC_PER_SEC, ns_to_asctime, getFolderSize, \
    BYTES_PER_EVENT
from LTTngAnalyzes.sched import Sched
from LTTngAnalyzes.mm import Mm
from ascii_graph import Pyasciigraph

try:
    from progressbar import ETA, Bar, Percentage, ProgressBar
    progressbar_available = True
except ImportError:
    progressbar_available = False


class MemTop():
    def __init__(self, traces):
        self.trace_start_ts = 0
        self.trace_end_ts = 0
        self.traces = traces
        self.tids = {}
        self.cpus = {}
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
        mm = Mm(self.mm, self.cpus, self.tids, None)
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
            elif event.name == "mm_page_alloc":
                mm.page_alloc(event)
            elif event.name == "mm_page_free":
                mm.page_free(event)
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

    def output(self, args, begin_ns, end_ns, final=0):
        count = 0
        limit = args.top
        graph = Pyasciigraph()
        values = []
        print('%s to %s' % (ns_to_asctime(begin_ns), ns_to_asctime(end_ns)))
        for tid in sorted(self.tids.values(),
                          key=operator.attrgetter('allocated_pages'),
                          reverse=True):
            if len(args.proc_list) > 0 and tid.comm not in args.proc_list:
                continue
            values.append(("%s (%d)" % (tid.comm, tid.tid),
                          tid.allocated_pages))
            count = count + 1
            if limit > 0 and count >= limit:
                break
        for line in graph.graph("Per-TID Memory Allocations", values,
                                unit=" pages"):
            print(line)

        values = []
        count = 0
        for tid in sorted(self.tids.values(),
                          key=operator.attrgetter('freed_pages'),
                          reverse=True):
            if len(args.proc_list) > 0 and tid.comm not in args.proc_list:
                continue
            values.append(("%s (%d)" % (tid.comm, tid.tid), tid.freed_pages))
            count = count + 1
            if limit > 0 and count >= limit:
                break
        for line in graph.graph("Per-TID Memory Deallocation", values,
                                unit=" pages"):
            print(line)
        print("\nTotal memory usage:\n- %d pages allocated\n- %d pages freed" %
              (self.mm["allocated_pages"], self.mm["freed_pages"]))

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
    args = parser.parse_args()
    args.proc_list = []

    traces = TraceCollection()
    handle = traces.add_trace(args.path, "ctf")
    if handle is None:
        sys.exit(1)

    c = MemTop(traces)

    c.run(args)

    traces.remove_trace(handle)
