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

import sys
import json
from babeltrace import *

NSEC_PER_SEC = 1000000000
MSEC_PER_NSEC = 1000000

class Process():
    def __init__(self):
        pass

class CPU():
    def __init__(self):
        pass

class CPUComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, CPU):
            return obj.cpu_pc
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)

class CPUAnalyzes():
    def __init__(self, traces):
        self.start_ts = 0
        self.end_ts = 0
        self.traces = traces
        self.tids = {}
        self.cpus = {}
        self.global_per_cpu = []

    def per_cpu(self, cpu_id, ts, next_tid):
        """Compute per-cpu usage"""
        if cpu_id in self.cpus:
            c = self.cpus[cpu_id]
            if c.start_task_ns != 0:
                c.cpu_ns += ts - c.start_task_ns
            # exclude swapper process
            if next_tid != 0:
                c.start_task_ns = ts
            else:
                c.start_task_ns = 0
        else:
            c = CPU()
            c.cpu_ns = 0
            # when we schedule a real task (not swapper)
            c.start_task_ns = ts
            # first activity on the CPU
            self.cpus[cpu_id] = c
            self.cpus[cpu_id].global_list = []

    def per_tid(self, ts, prev_tid, next_tid, next_comm):
        """Compute per-tid usage"""
        # per-tid usage
        if prev_tid in self.tids:
            p = self.tids[prev_tid]
            p.cpu_ns += (ts - p.last_sched)

        if not next_tid in self.tids:
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
            cpu_pc = self.cpus[cpu].cpu_pc
            total_cpu_pc += cpu_pc
            nb_cpu = len(self.cpus.keys())
            print("CPU %d : %d ns (%0.02f%%)" % (cpu, cpu_total_ns, cpu_pc))
        print("Total CPU Usage : %0.02f%%" % (total_cpu_pc / nb_cpu))
#        print(json.dumps(self.cpus, cls=CPUComplexEncoder))

    def json_per_cpu_report(self, start, end):
        out = {}
        out_per_cpu = {}
        out_ts = {"start" : int(start), "end" : int(end)}
        total_pc = 0
        for cpu in self.cpus.keys():
            out_per_cpu[cpu] = int(self.cpus[cpu].cpu_pc)
            total_pc += int(self.cpus[cpu].cpu_pc)
        out["per-cpu"] = out_per_cpu
        out["timestamp"] = out_ts
        out["total-cpu"] = int(total_pc / 4)
        print(json.dumps(out, indent=4))

    def json_global_per_cpu_report(self):
        a = []
        for cpu in self.cpus.keys():
            b = {}
            b["key"] = "CPU %d" % cpu
            b["values"] = self.cpus[cpu].global_list
            a.append(b)
        print(json.dumps(a))

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

    def reset_total(self, start_ts):
        for cpu in self.cpus.keys():
            self.cpus[cpu].cpu_ns = 0
            if self.cpus[cpu].start_task_ns != 0:
                self.cpus[cpu].start_task_ns = start_ts

        for tid in self.tids.keys():
            self.tids[tid].cpu_ns = 0

    def compute_stats(self, start_ns, end_ns):
        for cpu in self.cpus.keys():
            total_ns = end_ns - start_ns
            cpu_total_ns = self.cpus[cpu].cpu_ns
            self.cpus[cpu].cpu_pc = (cpu_total_ns * 100)/total_ns
            self.cpus[cpu].global_list.append((int(end_ns/MSEC_PER_NSEC),
                int(self.cpus[cpu].cpu_pc)))

    def run(self, refresh_sec = 0):
        """Process the trace"""
        current_sec = 0
        start_ns = 0
        end_ns = 0
        for event in self.traces.events:
            if self.start_ts == 0:
                self.start_ts = event.timestamp
            if start_ns == 0:
                start_ns = event.timestamp
            end_ns = event.timestamp
            if refresh_sec != 0:
                event_sec = event.timestamp / NSEC_PER_SEC
                if current_sec == 0:
                    current_sec = event_sec
                elif current_sec != event_sec and \
                        (current_sec + refresh_sec) <= event_sec:
                    self.compute_stats(start_ns, end_ns)
                    #self.text_report(current_sec, event_sec, info = 0, tid = 0)
                    #self.json_per_cpu_report(current_sec, event_sec)
                    self.reset_total(event.timestamp)
                    current_sec = event_sec
                    start_ns = event.timestamp
            self.end_ts = event.timestamp

            if event.name == "sched_switch":
                self.sched_switch(event)
        # stats for the whole trace
        if refresh_sec == 0:
            self.compute_stats(start_ns, end_ns)
            self.text_report(self.start_ts / NSEC_PER_SEC,
                self.end_ts / NSEC_PER_SEC, tid = 1)
        else:
            self.compute_stats(start_ns, end_ns)
#            self.text_report(current_sec, self.end_ts / NSEC_PER_SEC,
#                info = 0, tid = 0)
            #self.json_per_cpu_report(current_sec, event_sec)
        self.json_global_per_cpu_report()

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
