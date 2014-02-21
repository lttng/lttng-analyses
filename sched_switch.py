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

NSEC_PER_SEC = 1000000000

class Process():
    def __init__(self):
        pass

class CPU():
    def __init__(self):
        pass

class CPUAnalyzes():
    def __init__(self, traces):
        self.start_ts = 0
        self.end_ts = 0
        self.traces = traces
        self.tids = {}
        self.cpus = {}

    def per_cpu(self, cpu_id, ts, next_tid):
        """Compute per-cpu usage"""
        if self.cpus.has_key(cpu_id):
            c = self.cpus[cpu_id]
            if c.start_ns != 0:
                c.cpu_ns += ts - c.start_ns
            # exclude swapper process
            if next_tid != 0:
                c.start_ns = ts
            else:
                c.start_ns = 0
        else:
            c = CPU()
            c.cpu_ns = 0
            c.start_ns = ts
            self.cpus[cpu_id] = c

    def per_tid(self, ts, prev_tid, next_tid, next_comm):
        """Compute per-tid usage"""
        # per-tid usage
        if self.tids.has_key(prev_tid):
            p = self.tids[prev_tid]
            p.cpu_ns += (ts - p.last_sched)

        if not self.tids.has_key(next_tid):
            p = Process()
            p.tid = next_tid
            p.comm = next_comm
            p.cpu_ns = 0
            self.tids[next_tid] = p
        else:
            p = self.tids[next_tid]
        p.last_sched = ts

    def sched_switch(self, event):
        """Handle sched_switch event"""
        prev_tid = event["prev_tid"]
        next_comm = event["next_comm"]
        next_tid = event["next_tid"]
        cpu_id = event["cpu_id"]

        self.per_cpu(cpu_id, event.timestamp, next_tid)
        self.per_tid(event.timestamp, prev_tid, next_tid, next_comm)

    def text_per_pid_report(self, total_ns):
        print("\n### Per-TID Usage ###")
        for tid in self.tids.keys():
            print("%s (%d) : %0.02f%%" % (self.tids[tid].comm, tid,
                    ((self.tids[tid].cpu_ns * 100)/ total_ns)))

    def text_per_cpu_report(self, total_ns):
        print("### Per-CPU Usage ###")
        total_cpu_pc = 0
        for cpu in self.cpus.keys():
            cpu_total_ns = self.cpus[cpu].cpu_ns
            cpu_pc = (cpu_total_ns * 100)/total_ns
            total_cpu_pc += cpu_pc
            nb_cpu = len(self.cpus.keys())
            print("CPU %d : %d ns (%0.02f%%)" % (cpu, cpu_total_ns, cpu_pc))
        print("Total CPU Usage : %0.02f%%" % (total_cpu_pc / nb_cpu))

    def text_trace_info(self, total_ns):
        print("### Trace info ###")
        print("Start : %lu\nEnd: %lu" % (self.start_ts, self.end_ts))
        print("Total ns : %lu" % (total_ns))
        print("Total : %lu.%0.09lus\n" % (total_ns / NSEC_PER_SEC,
            total_ns % NSEC_PER_SEC))

    def text_report(self, begin_sec, end_sec, info = 1, cpu = 1, tid = 1):
        print("[%lu:%lu]" % (begin_sec, end_sec))
        total_ns = self.end_ts - self.start_ts

        if info:
            self.text_trace_info(total_ns)
        if cpu:
            self.text_per_cpu_report(total_ns)
        if tid:
            self.text_per_pid_report(total_ns)

    def reset_total(self):
        for cpu in self.cpus.keys():
            self.cpus[cpu].cpu_ns = 0
        for tid in self.tids.keys():
            self.tids[tid].cpu_ns = 0

    def run(self, refresh_sec = 0):
        """Process the trace"""
        current_sec = 0
        for event in self.traces.events:
            if self.start_ts == 0:
                self.start_ts = event.timestamp
            if refresh_sec != 0:
                event_sec = event.timestamp/NSEC_PER_SEC
                if current_sec == 0:
                    current_sec = event_sec
                elif current_sec != event_sec and \
                        (current_sec + refresh_sec) <= event_sec:
                    self.text_report(current_sec, event_sec, info = 0, tid = 0)
                    self.reset_total()
                    current_sec = event_sec
            self.end_ts = event.timestamp

            if event.name == "sched_switch":
                self.sched_switch(event)
        # stats for the whole trace
        if refresh_sec == 0:
            self.text_report(self.start_ts / NSEC_PER_SEC,
                self.end_ts / NSEC_PER_SEC, tid = 0)
        else:
            self.text_report(current_sec, self.end_ts / NSEC_PER_SEC,
                info = 0, tid = 0)

if __name__ == "__main__":
    refresh_sec = 0
    if len(sys.argv) < 2:
        print("Usage: %s [refresh-sec] path/to/trace" % sys.argv[0])
        sys.exit(1)
    elif len(sys.argv) == 3:
        refresh_sec = int(sys.argv[1])

    traces = TraceCollection()
    ret = traces.add_trace(sys.argv[len(sys.argv)-1], "ctf")
    if ret is None:
        sys.exit(1)

    c = CPUAnalyzes(traces)
    c.run(refresh_sec)
