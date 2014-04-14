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
import shutil
import time
from babeltrace import *
from LTTngAnalyzes.common import *
from LTTngAnalyzes.sched import *
from LTTngAnalyzes.syscalls import *
from LTTngAnalyzes.block_bio import *
from LTTngAnalyzes.net import *
from LTTngAnalyzes.statedump import *
from analyzes import *
from ascii_graph import Pyasciigraph

class IOTop():
    def __init__(self, traces):
        self.trace_start_ts = 0
        self.trace_end_ts = 0
        self.traces = traces
        self.cpus = {}
        self.tids = {}
        self.disks = {}
        self.ifaces = {}
        self.syscalls = {}

    def run(self, args):
        """Process the trace"""
        self.current_sec = 0
        self.start_ns = 0
        self.end_ns = 0

        sched = Sched(self.cpus, self.tids)
        syscall = Syscalls(self.cpus, self.tids, self.syscalls)
        block_bio = BlockBio(self.cpus, self.disks)
        net = Net(self.ifaces)
        statedump = Statedump(self.tids)

        for event in self.traces.events:
            if self.start_ns == 0:
                self.start_ns = event.timestamp
            if self.trace_start_ts == 0:
                self.trace_start_ts = event.timestamp
            self.end_ns = event.timestamp
            self.check_refresh(args, event)
            self.trace_end_ts = event.timestamp

            if event.name == "sched_switch":
                sched.switch(event)
            elif event.name[0:4] == "sys_":
                syscall.entry(event)
            elif event.name == "exit_syscall":
                syscall.exit(event)
            elif event.name == "block_bio_complete" or \
                   event.name == "block_rq_complete":
                block_bio.complete(event)
            elif event.name == "block_bio_queue":
                block_bio.queue(event)
            elif event.name == "netif_receive_skb":
                net.recv(event)
            elif event.name == "net_dev_xmit":
                net.send(event)
            elif event.name == "sched_process_fork":
                sched.process_fork(event)
            elif event.name == "lttng_statedump_process_state":
                statedump.process_state(event)
            elif event.name == "lttng_statedump_file_descriptor":
                statedump.file_descriptor(event)
        if args.refresh == 0:
            # stats for the whole trace
            self.output(args, self.trace_start_ts, self.trace_end_ts, final=1)
        else:
            # stats only for the last segment
            self.output(args, self.start_ns, self.trace_end_ts,
                    final=1)

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

    def output_file_read(self, args):
        count = 0
        limit = args.top
        graph = Pyasciigraph()
        values = []
        files = {}
        for tid in self.tids.values():
            for fd in tid.fds.values():
                if not fd.filename in files.keys():
                    files[fd.filename] = {}
                    files[fd.filename]["read"] = fd.read
                    files[fd.filename]["write"] = fd.write
                    if fd.filename.startswith("pipe") or \
                            fd.filename.startswith("socket") or \
                            fd.filename.startswith("anon_inode"):
                        files[fd.filename]["name"] = "%s (%s)" % (fd.filename, tid.comm)
                    else:
                        files[fd.filename]["name"] = fd.filename
                    files[fd.filename]["other"] = "(%d %d)" % (fd.fd, tid.tid)
                else:
                    files[fd.filename]["read"] += fd.read
                    files[fd.filename]["write"] += fd.write
        for f in files.values():
            if f["read"] == 0:
                continue
            values.append(("%s %s %s" % (f["name"],
                convert_size(f["read"]), f["other"]), f["read"]))
            count = count + 1
            if limit > 0 and count >= limit:
                break
        for line in graph.graph('Files Read', values, sort=2):
            print(line)

    def output_read(self, args):
        count = 0
        limit = args.top
        graph = Pyasciigraph()
        values = []
        for tid in sorted(self.tids.values(),
                key=operator.attrgetter('read'), reverse=True):
            if len(args.proc_list) > 0 and tid.comm not in args.proc_list:
                continue
            values.append(("%s %s (%d)" % (convert_size(tid.read), tid.comm, \
                    tid.tid), tid.read))
            count = count + 1
            if limit > 0 and count >= limit:
                break
        for line in graph.graph('I/O Read', values):
            print(line)

    def output_write(self, args):
        count = 0
        limit = args.top
        graph = Pyasciigraph()
        values = []
        for tid in sorted(self.tids.values(),
                key=operator.attrgetter('write'), reverse=True):
            if len(args.proc_list) > 0 and tid.comm not in args.proc_list:
                continue
            values.append(("%s %s (%d)" % (convert_size(tid.write), tid.comm, \
                    tid.tid), tid.write))
            count = count + 1
            if limit > 0 and count >= limit:
                break
        for line in graph.graph('I/O Write', values):
            print(line)

    def output_nr_sector(self, args):
        count = 0
        graph = Pyasciigraph()
        values = []
        for disk in sorted(self.disks.values(),
                key=operator.attrgetter('nr_sector'), reverse=True):
            values.append((disk.name, disk.nr_sector))
        for line in graph.graph('Disk nr_sector', values):
            print(line)

    def output_nr_requests(self, args):
        count = 0
        graph = Pyasciigraph()
        values = []
        for disk in sorted(self.disks.values(),
                key=operator.attrgetter('nr_requests'), reverse=True):
            values.append((disk.name, disk.nr_requests))
        for line in graph.graph('Disk nr_requests', values):
            print(line)

    def output_dev_latency(self, args):
        count = 0
        graph = Pyasciigraph()
        values = []
        for disk in self.disks.values():
            if disk.completed_requests == 0:
                continue
            total = (disk.request_time / disk.completed_requests) / MSEC_PER_NSEC
            total = float("%0.03f" % total)
            values.append(("ms %s" % disk.name, total))
        for line in graph.graph('Disk request time/sector', values, sort=2):
            print(line)

    def output_net_recv_bytes(self, args):
        count = 0
        graph = Pyasciigraph()
        values = []
        for iface in sorted(self.ifaces.values(),
                key=operator.attrgetter('recv_bytes'), reverse=True):
            values.append(("%s %s" % (convert_size(iface.recv_bytes), iface.name),
                iface.recv_bytes))
        for line in graph.graph('Network recv_bytes', values):
            print(line)

    def output_net_sent_bytes(self, args):
        count = 0
        graph = Pyasciigraph()
        values = []
        for iface in sorted(self.ifaces.values(),
                key=operator.attrgetter('send_bytes'), reverse=True):
            values.append(("%s %s" % (convert_size(iface.send_bytes), iface.name),
                iface.send_bytes))
        for line in graph.graph('Network sent_bytes', values):
            print(line)

    def output(self, args, begin_ns, end_ns, final=0):
        print('%s to %s' % (ns_to_asctime(begin_ns), ns_to_asctime(end_ns)))
        self.output_read(args)
        self.output_file_read(args)
        self.output_write(args)
        self.output_nr_sector(args)
        self.output_nr_requests(args)
        self.output_dev_latency(args)
        self.output_net_recv_bytes(args)
        self.output_net_sent_bytes(args)

    def reset_total(self, start_ts):
        for dev in self.disks.keys():
            self.disks[dev].nr_sector = 0
            self.disks[dev].nr_requests = 0
            self.disks[dev].completed_requests = 0
            self.disks[dev].request_time = 0

        for iface in self.ifaces.keys():
            self.ifaces[iface].recv_bytes = 0
            self.ifaces[iface].recv_packets = 0
            self.ifaces[iface].send_bytes = 0
            self.ifaces[iface].send_packets = 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='I/O usage analysis')
    parser.add_argument('path', metavar="<path/to/trace>", help='Trace path')
    parser.add_argument('-r', '--refresh', type=int,
            help='Refresh period in seconds', default=0)
    parser.add_argument('--top', type=int, default=10,
            help='Limit to top X TIDs (default = 10)')
    args = parser.parse_args()
    args.proc_list = []

    traces = TraceCollection()
    handle = traces.add_trace(args.path, "ctf")
    if handle is None:
        sys.exit(1)

    c = IOTop(traces)

    c.run(args)

    traces.remove_trace(handle)
