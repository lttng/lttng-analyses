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
import operator
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

    def sched_switch_per_cpu(self, cpu_id, ts, next_tid):
        """Compute per-cpu usage"""
        if cpu_id in self.cpus:
            c = self.cpus[cpu_id]
            if c.start_task_ns != 0:
                c.cpu_ns += ts - c.start_task_ns
            # exclude swapper process
            if next_tid != 0:
                c.start_task_ns = ts
                c.current_tid = next_tid
            else:
                c.start_task_ns = 0
                c.current_tid = -1
        else:
            c = CPU()
            c.cpu_ns = 0
            c.current_tid = next_tid
            # when we schedule a real task (not swapper)
            c.start_task_ns = ts
            # first activity on the CPU
            self.cpus[cpu_id] = c
            self.cpus[cpu_id].total_per_cpu_pc_list = []

    def sched_switch_per_tid(self, ts, prev_tid, next_tid, next_comm, cpu_id):
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
            p.migrate_count = 0
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

        self.sched_switch_per_cpu(cpu_id, event.timestamp, next_tid)
        self.sched_switch_per_tid(event.timestamp, prev_tid, next_tid, next_comm, cpu_id)

    def sched_migrate_task(self, event):
        tid = event["tid"]
        if not tid in self.tids:
            p = Process()
            p.tid = tid
            p.comm = event["comm"]
            p.cpu_ns = 0
            p.migrate_count = 0
            self.tids[tid] = p
        else:
            p = self.tids[tid]
        p.migrate_count += 1
        pass

    def text_per_tid_report(self, total_ns, proc_list, limit=0):
        print("### Per-TID Usage ###")
        count = 0
        for tid in sorted(self.tids.values(),
                key=operator.attrgetter('cpu_ns'), reverse=True):
            if len(proc_list) > 0 and tid.comm not in proc_list:
                continue
            print("%s (%d) : %0.02f%%" % (tid.comm, tid.tid,
                ((tid.cpu_ns * 100) / total_ns)), end="")
            if tid.migrate_count > 0:
                print(""" (%d migration(s))""" % tid.migrate_count)
            else:
                print("")
            count = count + 1
            if limit > 0 and count >= limit:
                break


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

    def json_per_tid_report(self, start, end, proc_list):
        out = {}
        out_per_tid = {}
        out_ts = {"start" : int(start), "end" : int(end)}
        total_ns = end - start
        for tid in self.tids.keys():
            if len(proc_list) > 0 and not self.tids[tid].comm in proc_list:
                continue
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
        print("Total : %lu.%0.09lus" % (total_ns / NSEC_PER_SEC,
            total_ns % NSEC_PER_SEC))

    def text_report(self, begin_ns, end_ns, final, args):
        if not (args.info or args.cpu or args.tid):
            return
        if args.cpu or args.tid:
            print("[%lu:%lu]" % (begin_ns/NSEC_PER_SEC, end_ns/NSEC_PER_SEC))

        total_ns = end_ns - begin_ns

        if args.info and final:
            self.text_trace_info()
        if args.cpu:
            self.text_per_cpu_report(total_ns)
        if args.tid:
            self.text_per_tid_report(total_ns, args.display_proc_list, limit=args.top)

    def json_report(self, begin_ns, end_ns, final, args):
        if not (args.info or args.cpu or args.tid or args.overall):
            return
        if args.info and final:
            self.json_trace_info()
        if args.cpu:
            self.json_per_cpu_report(begin_ns, end_ns)
        if args.tid:
            self.json_per_tid_report(begin_ns, end_ns, args.display_proc_list)
        if args.overall and final:
            self.json_global_per_cpu_report()

    def output(self, args, begin_ns, end_ns, final=0):
        if args.text:
            self.text_report(begin_ns, end_ns, final, args)
            if not final and (args.cpu or args.tid):
                print("")
        if args.json:
            self.json_report(begin_ns, end_ns, final, args)

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
            self.output(args, self.start_ns, event.timestamp)
            self.reset_total(event.timestamp)
            self.current_sec = event_sec
            self.start_ns = event.timestamp

    def reset_total(self, start_ts):
        for cpu in self.cpus.keys():
            current_cpu = self.cpus[cpu]
            current_cpu.cpu_ns = 0
            if current_cpu.start_task_ns != 0:
                current_cpu.start_task_ns = start_ts
            if current_cpu.current_tid >= 0:
                self.tids[current_cpu.current_tid].last_sched = start_ts

        for tid in self.tids.keys():
            self.tids[tid].cpu_ns = 0
            self.tids[tid].migrate_count = 0

    def compute_stats(self):
        for cpu in self.cpus.keys():
            current_cpu = self.cpus[cpu]
            total_ns = self.end_ns - self.start_ns
            if current_cpu.start_task_ns != 0:
                current_cpu.cpu_ns += self.end_ns - current_cpu.start_task_ns
            cpu_total_ns = current_cpu.cpu_ns
            current_cpu.cpu_pc = (cpu_total_ns * 100)/total_ns
            if current_cpu.current_tid >= 0:
                self.tids[current_cpu.current_tid].cpu_ns += \
                    self.end_ns - current_cpu.start_task_ns

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
            #print("TS :", event.timestamp)
            self.end_ns = event.timestamp
            self.check_refresh(args, event)
            self.trace_end_ts = event.timestamp

            if event.name == "sched_switch":
                self.sched_switch(event)
            elif event.name == "sched_migrate_task":
                self.sched_migrate_task(event)
        if args.refresh == 0:
            # stats for the whole trace
            self.compute_stats()
            self.output(args, self.trace_start_ts, self.trace_end_ts, final=1)
        else:
            # stats only for the last segment
            self.compute_stats()
            self.output(args, self.start_ns, self.trace_end_ts,
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
    parser.add_argument('--top', type=int, default=0, help='Limit to top X TIDs')
    parser.add_argument('--name', type=str, default=0, help='Show results " \
            "only for the list of processes')
    args = parser.parse_args()

    if not args.json:
        args.text = True

    if not (args.cpu or args.tid or args.overall or args.info):
        args.cpu = True
        args.tid = True
        args.overall = True
        args.info = True
    args.display_proc_list = []
    if args.name:
        args.display_proc_list = args.name.split(",")

    traces = TraceCollection()
    ret = traces.add_trace(args.path, "ctf")
    if ret is None:
        sys.exit(1)

    c = CPUAnalyzes(traces)
    c.run(args)
