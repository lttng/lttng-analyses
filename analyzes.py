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
import os
import sys
import time
try:
    from babeltrace import TraceCollection
except ImportError:
    # quick fix for debian-based distros
    sys.path.append("/usr/local/lib/python%d.%d/site-packages" %
                    (sys.version_info.major, sys.version_info.minor))
    from babeltrace import TraceCollection
from LTTngAnalyzes.common import NSEC_PER_SEC
from LTTngAnalyzes.jsonreport import JsonReport
from LTTngAnalyzes.textreport import TextReport
from LTTngAnalyzes.graphitereport import GraphiteReport
from LTTngAnalyzes.state import State
from LTTngAnalyzes.progressbar import progressbar_setup, progressbar_update, \
    progressbar_finish


class Analyzes():
    def __init__(self, traces):
        self.trace_start_ts = 0
        self.trace_end_ts = 0
        self.traces = traces
        self.state = State()

    def output(self, args, begin_ns, end_ns, final=0):
        if args.text:
            r = TextReport(self.trace_start_ts, self.trace_end_ts,
                           self.state.cpus, self.state.tids,
                           self.state.syscalls, self.state.disks,
                           self.state.ifaces, self.state.mm)
            r.report(begin_ns, end_ns, final, args)
            if not final and (args.cpu or args.tid or args.disk or args.net):
                print("")
        if args.json:
            r = JsonReport(self.trace_start_ts, self.trace_end_ts,
                           self.state.cpus, self.state.tids)
            r.report(begin_ns, end_ns, final, args)
        if args.graphite:
            r = GraphiteReport(self.trace_start_ts, self.trace_end_ts,
                               self.state.cpus, self.state.tids,
                               self.state.syscalls, self.state.disks,
                               self.state.ifaces)
            r.report(begin_ns, end_ns, final, args)

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
        for cpu in self.state.cpus.keys():
            current_cpu = self.state.cpus[cpu]
            current_cpu.cpu_ns = 0
            if current_cpu.start_task_ns != 0:
                current_cpu.start_task_ns = start_ts
            if current_cpu.current_tid >= 0:
                self.state.tids[current_cpu.current_tid].last_sched = start_ts

        for tid in self.state.tids.keys():
            self.state.tids[tid].cpu_ns = 0
            self.state.tids[tid].migrate_count = 0
            self.state.tids[tid].read = 0
            self.state.tids[tid].write = 0
            self.state.tids[tid].allocated_pages = 0
            self.state.tids[tid].freed_pages = 0
            for syscall in self.state.tids[tid].syscalls.keys():
                self.state.tids[tid].syscalls[syscall].count = 0

        for syscall in self.state.syscalls.keys():
            if syscall == "total":
                continue
            self.state.syscalls[syscall].count = 0

        for dev in self.state.disks.keys():
            self.state.disks[dev].nr_sector = 0
            self.state.disks[dev].nr_requests = 0
            self.state.disks[dev].completed_requests = 0
            self.state.disks[dev].request_time = 0

        for iface in self.state.ifaces.keys():
            self.state.ifaces[iface].recv_bytes = 0
            self.state.ifaces[iface].recv_packets = 0
            self.state.ifaces[iface].send_bytes = 0
            self.state.ifaces[iface].send_packets = 0

    def clear(self):
        self.trace_start_ts = 0
        self.trace_end_ts = 0
        self.traces = traces
        self.state.tids = {}
        self.state.cpus = {}
        self.state.syscalls = {}
        self.state.disks = {}
        self.state.ifaces = {}

    def compute_stats(self):
        for cpu in self.state.cpus.keys():
            current_cpu = self.state.cpus[cpu]
            total_ns = self.end_ns - self.start_ns
            if current_cpu.start_task_ns != 0:
                current_cpu.cpu_ns += self.end_ns - current_cpu.start_task_ns
            cpu_total_ns = current_cpu.cpu_ns
            current_cpu.cpu_pc = (cpu_total_ns * 100)/total_ns
            if current_cpu.current_tid >= 0:
                self.state.tids[current_cpu.current_tid].cpu_ns += \
                    self.end_ns - current_cpu.start_task_ns

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
            elif event.name == "sched_migrate_task":
                self.state.sched.migrate_task(event)
            elif event.name == "sched_process_fork":
                self.state.sched.process_fork(event)
            elif event.name == "sched_process_exec":
                self.state.sched.process_exec(event)
            elif (event.name[0:4] == "sys_" or event.name[0:14] ==
                  "syscall_entry_") and (args.global_syscalls or
                                         args.tid_syscalls or
                                         args.fds):
                self.state.syscall.entry(event)
            elif (event.name == "exit_syscall" or event.name[0:13] ==
                  "syscall_exit_") and (args.global_syscalls or
                                        args.tid_syscalls or
                                        args.fds):
                self.state.syscall.exit(event, 1)
            elif event.name == "block_rq_complete":
                self.state.block.complete(event)
            elif event.name == "block_rq_issue":
                self.state.block.issue(event)
            elif event.name == "netif_receive_skb":
                self.state.net.recv(event)
            elif event.name == "net_dev_xmit":
                self.state.net.send(event)
            elif event.name == "lttng_statedump_process_state":
                self.state.statedump.process_state(event)
            elif event.name == "lttng_statedump_file_descriptor":
                self.state.statedump.file_descriptor(event)
            elif event.name == "self.state.mm_page_alloc":
                self.state.mm.page_alloc(event)
            elif event.name == "self.state.mm_page_free":
                self.state.mm.page_free(event)
        progressbar_finish(self, args)
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
    parser.add_argument('--graphite', action="store_true",
                        help='Output to graphite')
    parser.add_argument('--cpu', action="store_true",
                        help='Per-CPU stats (default)')
    parser.add_argument('--mem', action="store_true",
                        help='Memory usage stats (default)')
    parser.add_argument('--disk', action="store_true",
                        help='Per-Disk stats (default)')
    parser.add_argument('--tid', action="store_true",
                        help='Per-TID stats (default)')
    parser.add_argument('--net', action="store_true",
                        help='Per-interface network stats (default)')
    parser.add_argument('--global-syscalls', action="store_true",
                        help='Global syscalls (default)')
    parser.add_argument('--tid-syscalls', action="store_true",
                        help='Per-TID syscalls (default)')
    parser.add_argument('--fds', action="store_true",
                        help='Per-PID FD stats (default)')
    parser.add_argument('--overall', action="store_true",
                        help='Overall CPU Usage (default)')
    parser.add_argument('--info', action="store_true",
                        help='Trace info (default)')
    parser.add_argument('--top', type=int, default=0,
                        help='Limit to top X TIDs')
    parser.add_argument('--name', type=str, default=0,
                        help='Show results only for the list of processes')
    parser.add_argument('--no-progress', action="store_true",
                        help='Don\'t display the progress bar')
    args = parser.parse_args()

    if not args.json and not args.graphite:
        args.text = True

    if args.tid_syscalls or args.fds:
        args.tid = True

    if not (args.cpu or args.tid or args.overall or args.info or
            args.global_syscalls or args.tid_syscalls or args.disk
            or args.net or args.fds or args.mem):
        args.cpu = True
        args.tid = True
        args.overall = True
        args.disk = True
        args.info = True
        args.global_syscalls = True
        args.tid_syscalls = True
        args.net = True
        args.fds = True
        args.mem = True
    if args.name:
        args.global_syscalls = False
    args.display_proc_list = []
    if args.name:
        args.display_proc_list = args.name.split(",")

    while True:
        if args.graphite:
            events = "sched_switch,block_rq_complete,block_rq_issue," \
                     "netif_receive_skb,net_dev_xmit"
            os.system("lttng create graphite -o graphite-live >/dev/null")
            os.system("lttng enable-event -k %s -s graphite >/dev/null"
                      % events)
            os.system("lttng start graphite >/dev/null")
            time.sleep(2)
            os.system("lttng stop graphite >/dev/null")
            os.system("lttng destroy graphite >/dev/null")
        traces = TraceCollection()
        handle = traces.add_traces_recursive(args.path, "ctf")
        if handle is None:
            sys.exit(1)

        c = Analyzes(traces)
        c.run(args)
        c.clear()

        for h in handle.values():
            traces.remove_trace(h)

        if not args.graphite:
            break
