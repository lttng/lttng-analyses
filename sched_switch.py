#!/usr/bin/env python
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

import sys
from babeltrace import *

class Process():
    def __init__(self):
        pass

class CPU():
    def __init__(self, traces):
        self.start_ts = 0
        self.end_ts = 0
        self.traces = traces
        self.tids = {}

    def run(self):
        for event in self.traces.events:
            if self.start_ts == 0:
                self.start_ts = event.timestamp
            self.end_ts = event.timestamp

            if event.name != "sched_switch":
                continue

            prev_tid = event["prev_tid"]
            next_comm = event["next_comm"]
            next_tid = event["next_tid"]

            if self.tids.has_key(prev_tid):
                p = self.tids[prev_tid]
                p.cpu_ns += (event.timestamp - p.last_sched)

            if not self.tids.has_key(next_tid):
                p = Process()
                p.tid = next_tid
                p.comm = next_comm
                p.cpu_ns = 0
                self.tids[next_tid] = p
            else:
                p = self.tids[next_tid]
            p.last_sched = event.timestamp
        
        total_ns = self.end_ts - self.start_ts
        for tid in self.tids.keys():
            print("%s (%d) : %0.02f%%" % (self.tids[tid].comm, tid,
                    ((self.tids[tid].cpu_ns * 100)/ total_ns)))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: %s path/to/trace" % sys.argv[0])
        sys.exit(1)

    traces = TraceCollection()
    ret = traces.add_trace(sys.argv[len(sys.argv)-1], "ctf")
    if ret is None:
        sys.exit(1)

    c = CPU(traces)
    c.run()
