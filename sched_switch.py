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
import argparse
from babeltrace import *
from LTTngAnalyzes.common import *
from LTTngAnalyzes.jsonreport import *
from LTTngAnalyzes.textreport import *
from LTTngAnalyzes.sched_switch import *
from LTTngAnalyzes.sched_migrate_task import *
from LTTngAnalyzes.syscalls import *

class CPUAnalyzes():
    def __init__(self, traces):
        self.trace_start_ts = 0
        self.trace_end_ts = 0
        self.traces = traces
        self.tids = {}
        self.cpus = {}
        self.syscalls = {}

    def output(self, args, begin_ns, end_ns, final=0):
        if args.text:
            t = TextReport(self.trace_start_ts, self.trace_end_ts,
                    self.cpus, self.tids, self.syscalls)
            t.report(begin_ns, end_ns, final, args)
            if not final and (args.cpu or args.tid):
                print("")
        if args.json:
            j = JsonReport(self.trace_start_ts, self.trace_end_ts,
                self.cpus, self.tids)
            j.report(begin_ns, end_ns, final, args)

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

        for syscall in self.syscalls.keys():
            self.syscalls[syscall].count = 0

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

        sched_switch = SchedSwitch(self.cpus, self.tids)
        migrate_task = SchedMigrateTask(self.cpus, self.tids)
        syscall = Syscalls(self.cpus, self.tids, self.syscalls)

        for event in self.traces.events:
            if self.start_ns == 0:
                self.start_ns = event.timestamp
            if self.trace_start_ts == 0:
                self.trace_start_ts = event.timestamp
            self.end_ns = event.timestamp
            self.check_refresh(args, event)
            self.trace_end_ts = event.timestamp

            if event.name == "sched_switch":
                sched_switch.add(event)
            elif event.name == "sched_migrate_task":
                migrate_task.add(event)
            elif event.name[0:4] == "sys_":
                syscall.entry(event)
            elif event.name == "exit_syscall":
                syscall.exit(event)
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
    parser.add_argument('--text', action="store_true",
            help='Output in text (default)')
    parser.add_argument('--json', action="store_true",
            help='Output in JSON')
    parser.add_argument('--cpu', action="store_true",
            help='Per-CPU stats (default)')
    parser.add_argument('--tid', action="store_true",
            help='Per-TID stats (default)')
    parser.add_argument('--global-syscalls', action="store_true",
            help='Global syscalls (default)')
    parser.add_argument('--tid-syscalls', action="store_true",
            help='Per-TID syscalls (default)')
    parser.add_argument('--overall', action="store_true",
            help='Overall CPU Usage (default)')
    parser.add_argument('--info', action="store_true",
            help='Trace info (default)')
    parser.add_argument('--top', type=int, default=0,
            help='Limit to top X TIDs')
    parser.add_argument('--name', type=str, default=0,
            help='Show results only for the list of processes')
    args = parser.parse_args()

    if not args.json:
        args.text = True

    if not (args.cpu or args.tid or args.overall or args.info or \
            args.global_syscalls or args.tid_syscalls):
        args.cpu = True
        args.tid = True
        args.overall = True
        args.info = True
        args.global_syscalls = True
        args.tid_syscalls = True
    args.display_proc_list = []
    if args.name:
        args.display_proc_list = args.name.split(",")

    traces = TraceCollection()
    ret = traces.add_trace(args.path, "ctf")
    if ret is None:
        sys.exit(1)

    c = CPUAnalyzes(traces)
    c.run(args)
