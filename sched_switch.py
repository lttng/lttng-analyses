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
import argparse
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
        self.trace_start_ts = 0
        self.trace_end_ts = 0
        self.traces = traces
        self.tids = {}
        self.cpus = {}

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
            self.cpus[cpu_id].total_per_cpu_pc_list = []

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

    def text_per_tid_report(self, total_ns):
        print("\n### Per-TID Usage ###")
        for tid in self.tids.keys():
            print("%s (%d) : %0.02f%%" % (self.tids[tid].comm, tid,
                    ((self.tids[tid].cpu_ns * 100)/ total_ns)))

    def text_per_cpu_report(self, total_ns):
        print("### Per-CPU Usage ###")
        total_cpu_pc = 0
        nb_cpu = len(self.cpus.keys())
        for cpu in self.cpus.keys():
            cpu_total_ns = self.cpus[cpu].cpu_ns
            cpu_pc = self.cpus[cpu].cpu_pc
            total_cpu_pc += cpu_pc
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
            total_pc += out_per_cpu[cpu]
        out["per-cpu"] = out_per_cpu
        out["timestamp"] = out_ts
        out["total-cpu"] = int(total_pc / len(self.cpus.keys()))
        print(json.dumps(out, indent=4))

    def json_per_tid_report(self, start, end):
        out = {}
        out_per_tid = {}
        out_ts = {"start" : int(start), "end" : int(end)}
        total_ns = (end - start) * NSEC_PER_SEC
        for tid in self.tids.keys():
            proc = {}
            proc["procname"] = self.tids[tid].comm
            proc["percent"] = int((self.tids[tid].cpu_ns * 100)/ total_ns)
            out_per_tid[tid] = proc
        out["per-tid"] = out_per_tid
        out["timestamp"] = out_ts
        print(json.dumps(out, indent=4))

    def json_global_per_cpu_report(self):
        a = []
        for cpu in self.cpus.keys():
            b = {}
            b["key"] = "CPU %d" % cpu
            b["values"] = self.cpus[cpu].total_per_cpu_pc_list
            a.append(b)
        print(json.dumps(a))

    def json_trace_info(self):
        out = {}
        total_ns = self.trace_end_ts - self.trace_start_ts
        out["start"] = self.trace_start_ts
        out["end"] = self.trace_end_ts
        out["total_ns"] = total_ns
        out["total_sec"] = "%lu.%0.09lus" % ((total_ns / NSEC_PER_SEC,
                        total_ns % NSEC_PER_SEC))
        print(json.dumps(out, indent=4))

    def text_trace_info(self):
        total_ns = self.trace_end_ts - self.trace_start_ts
        print("### Trace info ###")
        print("Start : %lu\nEnd: %lu" % (self.trace_start_ts, self.trace_end_ts))
        print("Total ns : %lu" % (total_ns))
        print("Total : %lu.%0.09lus\n" % (total_ns / NSEC_PER_SEC,
            total_ns % NSEC_PER_SEC))

    def text_report(self, begin_sec, end_sec, final, info, cpu, tid, overall):
        if not (info or cpu or tid):
            return
        print("[%lu:%lu]" % (begin_sec, end_sec))
        total_ns = (end_sec - begin_sec) * NSEC_PER_SEC

        if info and final:
            self.text_trace_info()
        if cpu:
            self.text_per_cpu_report(total_ns)
        if tid:
            self.text_per_tid_report(total_ns)

    def json_report(self, begin_sec, end_sec, final, info, cpu, tid, overall):
        if not (info or cpu or tid or overall):
            return
        if info and final:
            self.json_trace_info()
        if cpu:
            self.json_per_cpu_report(begin_sec, end_sec)
        if tid:
            self.json_per_tid_report(begin_sec, end_sec)
        if overall and final:
            self.json_global_per_cpu_report()

    def output(self, args, begin, end, final=0):
        if args.text:
            self.text_report(begin, end, final, args.info, args.cpu,
                    args.tid, args.overall)
        if args.json:
            self.json_report(begin, end, final, args.info, args.cpu,
                    args.tid, args.overall)

    def check_refresh(self, args, event):
        """Check if we need to output something"""
        if args.refresh == 0:
            return
        event_sec = event.timestamp / NSEC_PER_SEC
        if self.current_sec == 0:
            self.current_sec = event_sec
        elif self.current_sec != event_sec and \
                (self.current_sec + args.refresh) <= event_sec:
            self.compute_stats()
            self.output(args, self.current_sec, event_sec)
            self.reset_total(event.timestamp)
            self.current_sec = event_sec
            self.start_ns = event.timestamp

    def reset_total(self, start_ts):
        for cpu in self.cpus.keys():
            self.cpus[cpu].cpu_ns = 0
            if self.cpus[cpu].start_task_ns != 0:
                self.cpus[cpu].start_task_ns = start_ts

        for tid in self.tids.keys():
            self.tids[tid].cpu_ns = 0

    def compute_stats(self):
        for cpu in self.cpus.keys():
            total_ns = self.end_ns - self.start_ns
            cpu_total_ns = self.cpus[cpu].cpu_ns
            self.cpus[cpu].cpu_pc = (cpu_total_ns * 100)/total_ns
            self.cpus[cpu].total_per_cpu_pc_list.append(
                    (int(self.end_ns/MSEC_PER_NSEC),
                        int(self.cpus[cpu].cpu_pc)))

    def run(self, args):
        """Process the trace"""
        self.current_sec = 0
        self.start_ns = 0
        self.end_ns = 0
        for event in self.traces.events:
            if self.start_ns == 0:
                self.start_ns = event.timestamp
            if self.trace_start_ts == 0:
                self.trace_start_ts = event.timestamp
            self.end_ns = event.timestamp

            self.check_refresh(args, event)

            self.trace_end_ts = event.timestamp

            if event.name == "sched_switch":
                self.sched_switch(event)
        # stats for the whole trace
        if args.refresh == 0:
            self.compute_stats()
            self.output(args, self.trace_start_ts / NSEC_PER_SEC,
                    self.trace_end_ts / NSEC_PER_SEC, final=1)
        else:
            self.compute_stats()
            self.output(args, self.current_sec, self.trace_end_ts / NSEC_PER_SEC,
                    final=1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='CPU usage analysis')
    parser.add_argument('path', metavar="<path/to/trace>", help='Trace path')
    parser.add_argument('-r', '--refresh', type=int,
            help='Refresh period in seconds', default=0)
    parser.add_argument('--text', action="store_true", help='Output in text (default)')
    parser.add_argument('--json', action="store_true", help='Output in JSON')
    parser.add_argument('--cpu', action="store_true", help='Per-CPU stats (default)')
    parser.add_argument('--tid', action="store_true", help='Per-TID stats (default)')
    parser.add_argument('--overall', action="store_true", help='Overall CPU Usage (default)')
    parser.add_argument('--info', action="store_true", help='Trace info (default)')
    args = parser.parse_args()

    if not args.json:
        args.text = True

    if not (args.cpu or args.tid or args.overall or args.info):
        args.cpu = True
        args.tid = True
        args.overall = True
        args.info = True

    traces = TraceCollection()
    ret = traces.add_trace(args.path, "ctf")
    if ret is None:
        sys.exit(1)

    c = CPUAnalyzes(traces)
    c.run(args)
