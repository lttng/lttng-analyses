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
from LTTngAnalyzes.block import Block
from LTTngAnalyzes.net import Net
from LTTngAnalyzes.statedump import Statedump
from LTTngAnalyzes.mm import Mm
try:
    from babeltrace import TraceCollection
except ImportError:
    # quick fix for debian-based distros
    sys.path.append("/usr/local/lib/python%d.%d/site-packages" %
                   (sys.version_info.major, sys.version_info.minor))
    from babeltrace import TraceCollection
from LTTngAnalyzes.common import convert_size, getFolderSize, \
    BYTES_PER_EVENT, MSEC_PER_NSEC, NSEC_PER_SEC, ns_to_asctime, \
    sec_to_nsec
from LTTngAnalyzes.sched import Sched
from LTTngAnalyzes.syscalls import Syscalls
from ascii_graph import Pyasciigraph

try:
    from progressbar import ETA, Bar, Percentage, ProgressBar
    progressbar_available = True
except ImportError:
    progressbar_available = False


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
        self.latency_hist = {}
        # prototyping stuff
        self.random = {}
        self.random["write_queue"] = 0
        self.dirty_pages = {}
        self.dirty_pages["pages"] = []
        self.dirty_pages["global_nr_dirty"] = -1
        self.dirty_pages["base_nr_dirty"] = -1

    def process_event(self, event, sched, syscall, block, net, statedump,
                      mm, started):
        if self.start_ns == 0:
            self.start_ns = event.timestamp
        if self.trace_start_ts == 0:
            self.trace_start_ts = event.timestamp
        self.end_ns = event.timestamp
        self.check_refresh(args, event)
        self.trace_end_ts = event.timestamp

        if event.name == "sched_switch":
            sched.switch(event)
        if event.name in ["sched_wakeup", "sched_wakeup_new"]:
            sched.wakeup(event)
        elif event.name[0:4] == "sys_" or event.name[0:14] == "syscall_entry_":
            syscall.entry(event)
        elif event.name == "writeback_pages_written":
            syscall.wb_pages(event)
        elif event.name == "mm_vmscan_wakeup_kswapd":
            syscall.wakeup_kswapd(event)
#        elif event.name == "writeback_global_dirty_state":
#            mm.writeback_global_dirty_state(event)
        elif event.name == "block_dirty_buffer":
            mm.block_dirty_buffer(event)
        elif event.name == "mm_page_free":
            syscall.page_free(event)
            mm.page_free(event)
        elif event.name == "mm_page_alloc":
            mm.page_alloc(event)
        elif event.name == "exit_syscall" or \
                event.name[0:13] == "syscall_exit_":
            syscall.exit(event, started)
        elif event.name == "block_rq_complete":
            block.complete(event)
        elif event.name == "block_rq_issue":
            block.issue(event)
        elif event.name == "block_bio_remap":
            block.remap(event)
        elif event.name == "block_bio_backmerge":
            block.backmerge(event)
        elif event.name == "netif_receive_skb":
            net.recv(event)
        elif event.name == "net_dev_xmit":
            net.send(event)
        elif event.name == "sched_process_fork":
            sched.process_fork(event)
        elif event.name == "sched_process_exec":
            sched.process_exec(event)
        elif event.name == "lttng_statedump_process_state":
            statedump.process_state(event)
        elif event.name == "lttng_statedump_file_descriptor":
            statedump.file_descriptor(event)
        elif event.name == "lttng_statedump_block_device":
            statedump.block_device(event)

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

        sched = Sched(self.cpus, self.tids, self.dirty_pages)
        syscall = Syscalls(self.cpus, self.tids, self.syscalls,
                           self.dirty_pages,
                           names=args.names, latency=args.latency,
                           latency_hist=self.latency_hist,
                           seconds=args.seconds)
        block = Block(self.cpus, self.disks, self.tids)
        net = Net(self.ifaces, self.cpus, self.tids)
        statedump = Statedump(self.tids, self.disks)
        mm = Mm(self.cpus, self.tids, self.dirty_pages)

        event_count = 0
        if not args.begin:
            started = 1
        else:
            started = 0
        for event in self.traces.events:
            if not args.no_progress:
                try:
                    pbar.update(event_count)
                except ValueError:
                    pass
            event_count += 1
            if args.begin and started == 0 and event.timestamp >= args.begin:
                started = 1
                self.trace_start_ts = event.timestamp
                self.reset_total(event.timestamp)
            if args.end and event.timestamp > args.end:
                break
            self.process_event(event, sched, syscall, block, net,
                               statedump, mm, started)
        if not args.no_progress:
            pbar.finish()
            print
        if args.refresh == 0:
            # stats for the whole trace
            self.output(args, self.trace_start_ts, self.trace_end_ts, final=1)
        else:
            # stats only for the last segment
            self.output(args, self.start_ns, self.trace_end_ts, final=1)
        # XXX : debug
        # block.dump_orphan_requests()

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

    def output_file_read_write(self, args):
        count = 0
        limit = args.top
        graph = Pyasciigraph()
        values = []
        files = {}
        for tid in self.tids.values():
            for fd in tid.fds.values():
                if fd.filename not in files.keys():
                    files[fd.filename] = {}
                    files[fd.filename]["read"] = fd.read
                    files[fd.filename]["write"] = fd.write
                    if fd.filename.startswith("pipe") or \
                            fd.filename.startswith("socket") or \
                            fd.filename.startswith("anon_inode"):
                        files[fd.filename]["name"] = "%s (%s)" % (fd.filename,
                                                                  tid.comm)
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
        for f in files.values():
            if f["write"] == 0:
                continue
            values.append(("%s %s %s" % (f["name"],
                           convert_size(f["write"]), f["other"]), f["write"]))
            count = count + 1
            if limit > 0 and count >= limit:
                break
        for line in graph.graph('Files Write', values, sort=2):
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
            values.append(("%s %s (%d), %s disk, %s net, %s block, "
                           "%s unknown" %
                           (convert_size(tid.read), tid.comm,
                            tid.tid, convert_size(tid.disk_read),
                            convert_size(tid.net_read),
                            convert_size(tid.block_read),
                            convert_size(tid.unk_read)), tid.read))
            count = count + 1
            if limit > 0 and count >= limit:
                break
        for line in graph.graph('Syscall I/O Read', values):
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
            values.append(("%s %s (%d), %s disk, %s net, %s block, "
                           "%s unknown" %
                           (convert_size(tid.write), tid.comm,
                            tid.tid, convert_size(tid.disk_write),
                            convert_size(tid.net_write),
                            convert_size(tid.block_write),
                            convert_size(tid.unk_write)), tid.write))
            count = count + 1
            if limit > 0 and count >= limit:
                break
        for line in graph.graph('Syscall I/O Write', values):
            print(line)

    def disk_output_read(self, args):
        count = 0
        limit = args.top
        graph = Pyasciigraph()
        values = []
        for tid in sorted(self.tids.values(),
                          key=operator.attrgetter('block_read'), reverse=True):
            if len(args.proc_list) > 0 and tid.comm not in args.proc_list:
                continue
            values.append(("%s %s (%d)" % (convert_size(tid.block_read),
                                           tid.comm, tid.tid), tid.block_read))
            count = count + 1
            if limit > 0 and count >= limit:
                break
        for line in graph.graph('Block I/O Read', values):
            print(line)

    def disk_output_write(self, args):
        count = 0
        limit = args.top
        graph = Pyasciigraph()
        values = []
        for tid in sorted(self.tids.values(),
                          key=operator.attrgetter('block_write'),
                          reverse=True):
            if len(args.proc_list) > 0 and tid.comm not in args.proc_list:
                continue
            values.append(("%s %s (%d)" % (convert_size(tid.block_write),
                                           tid.comm,
                                           tid.tid), tid.block_write))
            count = count + 1
            if limit > 0 and count >= limit:
                break
        for line in graph.graph('Block I/O Write', values):
            print(line)

    def output_nr_sector(self, args):
        graph = Pyasciigraph()
        values = []
        for disk in sorted(self.disks.values(),
                           key=operator.attrgetter('nr_sector'), reverse=True):
            if disk.nr_sector == 0:
                continue
            values.append((disk.prettyname, disk.nr_sector))
        for line in graph.graph('Disk nr_sector', values):
            print(line)

    def output_nr_requests(self, args):
        graph = Pyasciigraph()
        values = []
        for disk in sorted(self.disks.values(),
                           key=operator.attrgetter('nr_requests'),
                           reverse=True):
            if disk.nr_sector == 0:
                continue
            values.append((disk.prettyname, disk.nr_requests))
        for line in graph.graph('Disk nr_requests', values):
            print(line)

    def output_dev_latency(self, args):
        graph = Pyasciigraph()
        values = []
        for disk in self.disks.values():
            if disk.completed_requests == 0:
                continue
            total = (disk.request_time / disk.completed_requests) \
                / MSEC_PER_NSEC
            total = float("%0.03f" % total)
            values.append(("ms %s" % disk.prettyname, total))
        for line in graph.graph('Disk request time/sector', values, sort=2):
            print(line)

    def output_net_recv_bytes(self, args):
        graph = Pyasciigraph()
        values = []
        for iface in sorted(self.ifaces.values(),
                            key=operator.attrgetter('recv_bytes'),
                            reverse=True):
            values.append(("%s %s" % (convert_size(iface.recv_bytes),
                                      iface.name),
                          iface.recv_bytes))
        for line in graph.graph('Network recv_bytes', values):
            print(line)

    def output_net_sent_bytes(self, args):
        graph = Pyasciigraph()
        values = []
        for iface in sorted(self.ifaces.values(),
                            key=operator.attrgetter('send_bytes'),
                            reverse=True):
            values.append(("%s %s" % (convert_size(iface.send_bytes),
                                      iface.name),
                          iface.send_bytes))
        for line in graph.graph('Network sent_bytes', values):
            print(line)

    def output_latencies(self, args):
        graph = Pyasciigraph()
        for proc in self.latency_hist.keys():
            values = []
            for v in self.latency_hist[proc]:
                values.append(("%s" % (v[0]), v[1]))
            for line in graph.graph('%s requests latency (ms)' % proc, values):
                print(line)

    def output(self, args, begin_ns, end_ns, final=0):
        print('%s to %s' % (ns_to_asctime(begin_ns), ns_to_asctime(end_ns)))
        self.output_read(args)
        self.output_write(args)
        self.disk_output_read(args)
        self.disk_output_write(args)
        self.output_file_read_write(args)
        self.output_nr_sector(args)
        self.output_nr_requests(args)
        self.output_dev_latency(args)
        self.output_net_recv_bytes(args)
        self.output_net_sent_bytes(args)
        self.output_latencies(args)

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

        for tid in self.tids.values():
            for fd in tid.fds.values():
                fd.read = 0
                fd.write = 0
                fd.block_read = 0
                fd.block_write = 0
                fd.open = 0
                fd.close = 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='I/O usage analysis')
    parser.add_argument('path', metavar="<path/to/trace>", help='Trace path')
    parser.add_argument('-r', '--refresh', type=int,
                        help='Refresh period in seconds', default=0)
    parser.add_argument('--top', type=int, default=10,
                        help='Limit to top X TIDs (default = 10)')
    parser.add_argument('--name', type=str, default=0,
                        help='Show the I/O latency for this list of processes '
                             '("all" accepted)')
    parser.add_argument('--latency', type=int, default=-1,
                        help='Only show I/O requests with a latency above '
                             'this threshold (ms)')
    parser.add_argument('--no-progress', action="store_true",
                        help='Don\'t display the progress bar')
    parser.add_argument('--begin', type=float,
                        help='start time in seconds from epoch '
                             '(e.g. 1394643671.032202563)')
    parser.add_argument('--end', type=float,
                        help='end time in seconds from epoch '
                             '(e.g.: 1394643671.032202563)')
    parser.add_argument('--seconds', action="store_true",
                        help='display time in seconds since epoch')
    args = parser.parse_args()
    args.proc_list = []

    if args.name:
        args.names = args.name.split(",")
    else:
        args.names = None

    if args.begin:
        args.begin = sec_to_nsec(args.begin)
    if args.end:
        args.end = sec_to_nsec(args.end)

    traces = TraceCollection()
    handle = traces.add_trace(args.path, "ctf")
    if handle is None:
        sys.exit(1)

    c = IOTop(traces)

    c.run(args)

    traces.remove_trace(handle)
