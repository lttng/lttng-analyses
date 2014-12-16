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
from LTTngAnalyzes.state import State
from LTTngAnalyzes.common import convert_size, MSEC_PER_NSEC, NSEC_PER_SEC, \
    ns_to_asctime, sec_to_nsec
from LTTngAnalyzes.progressbar import progressbar_setup, progressbar_update, \
    progressbar_finish
from ascii_graph import Pyasciigraph


class IOTop():
    def __init__(self, traces):
        self.trace_start_ts = 0
        self.trace_end_ts = 0
        self.traces = traces
        self.latency_hist = {}
        self.state = State()

    def process_event(self, event, started):
        if self.start_ns == 0:
            self.start_ns = event.timestamp
        if self.trace_start_ts == 0:
            self.trace_start_ts = event.timestamp
        self.end_ns = event.timestamp
        self.check_refresh(args, event)
        self.trace_end_ts = event.timestamp

        if event.name == "sched_switch":
            self.state.sched.switch(event)
        if event.name in ["sched_wakeup", "sched_wakeup_new"]:
            self.state.sched.wakeup(event)
        elif event.name[0:4] == "sys_" or event.name[0:14] == "syscall_entry_":
            self.state.syscall.entry(event)
        elif event.name == "writeback_pages_written":
            self.state.syscall.wb_pages(event)
        elif event.name == "mm_vmscan_wakeup_kswapd":
            self.state.syscall.wakeup_kswapd(event)
#        elif event.name == "writeback_global_dirty_state":
#            self.state.mem.writeback_global_dirty_state(event)
        elif event.name == "block_dirty_buffer":
            self.state.mem.block_dirty_buffer(event)
        elif event.name == "mm_page_free":
            self.state.syscall.page_free(event)
            self.state.mem.page_free(event)
        elif event.name == "mm_page_alloc":
            self.state.mem.page_alloc(event)
        elif event.name == "exit_syscall" or \
                event.name[0:13] == "syscall_exit_":
            self.state.syscall.exit(event, started)
        elif event.name == "block_rq_complete":
            self.state.block.complete(event)
        elif event.name == "block_rq_issue":
            self.state.block.issue(event)
        elif event.name == "block_bio_remap":
            self.state.block.remap(event)
        elif event.name == "block_bio_backmerge":
            self.state.block.backmerge(event)
        elif event.name == "netif_receive_skb":
            self.state.net.recv(event)
        elif event.name == "net_dev_xmit":
            self.state.net.send(event)
        elif event.name == "sched_process_fork":
            self.state.sched.process_fork(event)
        elif event.name == "sched_process_exec":
            self.state.sched.process_exec(event)
        elif event.name == "lttng_statedump_process_state":
            self.state.statedump.process_state(event)
        elif event.name == "lttng_statedump_file_descriptor":
            self.state.statedump.file_descriptor(event)
        elif event.name == "lttng_statedump_block_device":
            self.state.statedump.block_device(event)

    def run(self, args):
        """Process the trace"""
        self.current_sec = 0
        self.start_ns = 0
        self.end_ns = 0

        progressbar_setup(self, args)

        if not args.begin:
            started = 1
        else:
            started = 0
        for event in self.traces.events:
            progressbar_update(self, args)
            if args.begin and started == 0 and event.timestamp >= args.begin:
                started = 1
                self.trace_start_ts = event.timestamp
                self.reset_total(event.timestamp)
            if args.end and event.timestamp > args.end:
                break
            self.process_event(event, started)
        progressbar_finish(self, args)
        if args.refresh == 0:
            # stats for the whole trace
            self.output(args, self.trace_start_ts, self.trace_end_ts, final=1)
        else:
            # stats only for the last segment
            self.output(args, self.start_ns, self.trace_end_ts, final=1)
        # XXX : debug
        # self.state.block.dump_orphan_requests()

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

    def add_fd_dict(self, tid, fd, files):
        if fd.read == 0 and fd.write == 0:
            return
        if fd.filename.startswith("pipe") or \
                fd.filename.startswith("socket") or \
                fd.filename.startswith("anon_inode") or \
                fd.filename.startswith("unknown"):
            filename = "%s (%s)" % (fd.filename, tid.comm)
            files[filename] = {}
            files[filename]["read"] = fd.read
            files[filename]["write"] = fd.write
            files[filename]["name"] = filename
            files[filename]["other"] = ["(fd %d in %s (%d))" % (fd.fd,
                                        tid.comm, tid.tid)]
        else:
            # merge counters of shared files
            filename = fd.filename
            if filename not in files.keys():
                files[filename] = {}
                files[filename]["read"] = fd.read
                files[filename]["write"] = fd.write
                files[filename]["name"] = filename
                files[filename]["other"] = ["(fd %d in %s (%d)" %
                                            (fd.fd, tid.comm, tid.tid)]
                files[filename]["tids"] = [tid.tid]
            else:
                files[filename]["read"] += fd.read
                files[filename]["write"] += fd.write
                files[filename]["other"].append("(fd %d in %s (%d)" %
                                                (fd.fd, tid.comm,
                                                 tid.tid))

    def create_files_dict(self):
        files = {}
        for tid in self.state.tids.values():
            for fd in tid.fds.values():
                self.add_fd_dict(tid, fd, files)
            for fd in tid.closed_fds.values():
                self.add_fd_dict(tid, fd, files)
        return files

    def output_print_file_read(self, args, files):
        count = 0
        limit = args.top
        graph = Pyasciigraph()
        values = []
        sorted_f = sorted(files.items(), key=lambda files: files[1]['read'],
                          reverse=True)
        for f in sorted_f:
            if f[1]["read"] == 0:
                continue
            info_fmt = "{:>10}".format(convert_size(f[1]["read"],
                                       padding_after=True))
            values.append(("%s %s %s" % (info_fmt,
                                         f[1]["name"],
                                         str(f[1]["other"])[1:-1]),
                           f[1]["read"]))
            count = count + 1
            if limit > 0 and count >= limit:
                break
        for line in graph.graph('Files Read', values, sort=2,
                                with_value=False):
            print(line)

    def output_print_file_write(self, args, files):
        # Compute files read
        count = 0
        limit = args.top
        graph = Pyasciigraph()
        values = []
        sorted_f = sorted(files.items(), key=lambda files: files[1]['write'],
                          reverse=True)
        for f in sorted_f:
            if f[1]["write"] == 0:
                continue
            info_fmt = "{:>10}".format(convert_size(f[1]["write"],
                                       padding_after=True))
            values.append(("%s %s %s" % (info_fmt,
                                         f[1]["name"],
                                         str(f[1]["other"])[1:-1]),
                           f[1]["write"]))
            count = count + 1
            if limit > 0 and count >= limit:
                break
        for line in graph.graph('Files Write', values, sort=2,
                                with_value=False):
            print(line)

    def output_file_read_write(self, args):
        files = self.create_files_dict()
        self.output_print_file_read(args, files)
        self.output_print_file_write(args, files)

    def output_read(self, args):
        count = 0
        limit = args.top
        graph = Pyasciigraph()
        values = []
        for tid in sorted(self.state.tids.values(),
                          key=operator.attrgetter('read'), reverse=True):
            if len(args.proc_list) > 0 and tid.comm not in args.proc_list:
                continue
            info_fmt = "{:>10} {:<25} {:>9} disk {:>9} net {:>9} block " \
                       "{:>9} unknown"
            values.append((info_fmt.format(
                           convert_size(tid.read, padding_after=True),
                           "%s (%d)" % (tid.comm, tid.tid),
                           convert_size(tid.disk_read, padding_before=True),
                           convert_size(tid.net_read, padding_before=True),
                           convert_size(tid.block_read, padding_before=True),
                           convert_size(tid.unk_read, padding_before=True)),
                           tid.read))
            count = count + 1
            if limit > 0 and count >= limit:
                break
        for line in graph.graph('Syscall I/O Read', values, with_value=False):
            print(line)

    def output_write(self, args):
        count = 0
        limit = args.top
        graph = Pyasciigraph()
        values = []
        for tid in sorted(self.state.tids.values(),
                          key=operator.attrgetter('write'), reverse=True):
            if len(args.proc_list) > 0 and tid.comm not in args.proc_list:
                continue
            info_fmt = "{:>10} {:<25} {:>9} disk {:>9} net {:>9} block " \
                       "{:>9} unknown"
            values.append((info_fmt.format(
                           convert_size(tid.write, padding_after=True),
                           "%s (%d)" % (tid.comm, tid.tid),
                           convert_size(tid.disk_write, padding_before=True),
                           convert_size(tid.net_write, padding_before=True),
                           convert_size(tid.block_write, padding_before=True),
                           convert_size(tid.unk_write, padding_before=True)),
                           tid.write))
            count = count + 1
            if limit > 0 and count >= limit:
                break
        for line in graph.graph('Syscall I/O Write', values, with_value=False):
            print(line)

    def disk_output_read(self, args):
        count = 0
        limit = args.top
        graph = Pyasciigraph()
        values = []
        for tid in sorted(self.state.tids.values(),
                          key=operator.attrgetter('block_read'), reverse=True):
            if tid.block_read == 0:
                continue
            if len(args.proc_list) > 0 and tid.comm not in args.proc_list:
                continue
            info_fmt = "{:>10} {:<22}"
            values.append((info_fmt.format(convert_size(tid.block_read,
                                           padding_after=True),
                                           "%s (tid=%d)" % (tid.comm,
                                                            tid.tid)),
                           tid.block_read))
            count = count + 1
            if limit > 0 and count >= limit:
                break
        for line in graph.graph('Block I/O Read', values, with_value=False):
            print(line)

    def disk_output_write(self, args):
        count = 0
        limit = args.top
        graph = Pyasciigraph()
        values = []
        for tid in sorted(self.state.tids.values(),
                          key=operator.attrgetter('block_write'),
                          reverse=True):
            if tid.block_write == 0:
                continue
            if len(args.proc_list) > 0 and tid.comm not in args.proc_list:
                continue
            info_fmt = "{:>10} {:<22}"
            values.append((info_fmt.format(convert_size(tid.block_write,
                                           padding_after=True),
                                           "%s (tid=%d)" % (tid.comm,
                                                            tid.tid)),
                           tid.block_write))
            count = count + 1
            if limit > 0 and count >= limit:
                break
        for line in graph.graph('Block I/O Write', values, with_value=False):
            print(line)

    def output_nr_sector(self, args):
        graph = Pyasciigraph()
        values = []
        for disk in sorted(self.state.disks.values(),
                           key=operator.attrgetter('nr_sector'), reverse=True):
            if disk.nr_sector == 0:
                continue
            values.append((disk.prettyname, disk.nr_sector))
        for line in graph.graph('Disk nr_sector', values, unit=" sectors"):
            print(line)

    def output_nr_requests(self, args):
        graph = Pyasciigraph()
        values = []
        for disk in sorted(self.state.disks.values(),
                           key=operator.attrgetter('nr_requests'),
                           reverse=True):
            if disk.nr_sector == 0:
                continue
            values.append((disk.prettyname, disk.nr_requests))
        for line in graph.graph('Disk nr_requests', values, unit=" requests"):
            print(line)

    def output_dev_latency(self, args):
        graph = Pyasciigraph()
        values = []
        for disk in self.state.disks.values():
            if disk.completed_requests == 0:
                continue
            total = (disk.request_time / disk.completed_requests) \
                / MSEC_PER_NSEC
            total = float("%0.03f" % total)
            values.append(("%s" % disk.prettyname, total))
        for line in graph.graph('Disk request time/sector', values, sort=2,
                                unit=" ms"):
            print(line)

    def output_net_recv_bytes(self, args):
        graph = Pyasciigraph()
        values = []
        for iface in sorted(self.state.ifaces.values(),
                            key=operator.attrgetter('recv_bytes'),
                            reverse=True):
            values.append(("%s %s" % (convert_size(iface.recv_bytes),
                                      iface.name),
                          iface.recv_bytes))
        for line in graph.graph('Network recv_bytes', values,
                                with_value=False):
            print(line)

    def output_net_sent_bytes(self, args):
        graph = Pyasciigraph()
        values = []
        for iface in sorted(self.state.ifaces.values(),
                            key=operator.attrgetter('send_bytes'),
                            reverse=True):
            values.append(("%s %s" % (convert_size(iface.send_bytes),
                                      iface.name),
                          iface.send_bytes))
        for line in graph.graph('Network sent_bytes', values,
                                with_value=False):
            print(line)

    def output_latencies(self, args):
        graph = Pyasciigraph()
        for proc in self.latency_hist.keys():
            values = []
            for v in self.latency_hist[proc]:
                values.append(("%s" % (v[0]), v[1]))
            for line in graph.graph('%s requests latency (ms)' % proc, values,
                                    unit=" ms"):
                print(line)

    def output(self, args, begin_ns, end_ns, final=0):
        print('%s to %s' % (ns_to_asctime(begin_ns), ns_to_asctime(end_ns)))
        self.output_read(args)
        self.output_write(args)
        self.output_file_read_write(args)
        self.disk_output_read(args)
        self.disk_output_write(args)
        self.output_nr_sector(args)
        self.output_nr_requests(args)
        self.output_dev_latency(args)
        self.output_net_recv_bytes(args)
        self.output_net_sent_bytes(args)
        self.output_latencies(args)

    def reset_total(self, start_ts):
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

        for tid in self.state.tids.values():
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
    handle = traces.add_traces_recursive(args.path, "ctf")
    if handle is None:
        sys.exit(1)

    c = IOTop(traces)

    c.run(args)

    for h in handle.values():
        traces.remove_trace(h)
