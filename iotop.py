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
import statistics
try:
    from babeltrace import TraceCollection
except ImportError:
    # quick fix for debian-based distros
    sys.path.append("/usr/local/lib/python%d.%d/site-packages" %
                    (sys.version_info.major, sys.version_info.minor))
    from babeltrace import TraceCollection
from LTTngAnalyzes.state import State
from LTTngAnalyzes.common import convert_size, MSEC_PER_NSEC, NSEC_PER_SEC, \
    ns_to_asctime, date_to_epoch_nsec, is_multi_day_trace_collection, \
    IORequest, Syscalls_stats, ns_to_hour_nsec, str_to_bytes, SyscallConsts
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
            files[filename]["other"] = ["fd %d in %s (%d)" % (fd.fd,
                                        tid.comm, tid.pid)]
        else:
            # merge counters of shared files
            filename = fd.filename
            if filename not in files.keys():
                files[filename] = {}
                files[filename]["read"] = fd.read
                files[filename]["write"] = fd.write
                files[filename]["name"] = filename
                files[filename]["other"] = ["fd %d in %s (%d)" %
                                            (fd.fd, tid.comm, tid.pid)]
                files[filename]["tids"] = [tid.tid]
            else:
                files[filename]["read"] += fd.read
                files[filename]["write"] += fd.write
                files[filename]["other"].append("fd %d in %s (%d)" %
                                                (fd.fd, tid.comm,
                                                 tid.pid))

    def create_files_dict(self):
        files = {}
        for tid in self.state.tids.values():
            if not self.filter_process(args, tid):
                continue
            for fd in tid.fds.values():
                self.add_fd_dict(tid, fd, files)
            for fd in tid.closed_fds.values():
                self.add_fd_dict(tid, fd, files)
        return files

    # iotop functions
    def iotop_output_print_file_read(self, args, files):
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

    def iotop_output_print_file_write(self, args, files):
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

    def iotop_output_file_read_write(self, args):
        files = self.create_files_dict()
        self.iotop_output_print_file_read(args, files)
        self.iotop_output_print_file_write(args, files)

    def filter_process(self, args, proc):
        if args.proc_list and proc.comm not in args.proc_list:
            return False
        if args.pid_filter_list and str(proc.pid) not in args.pid_filter_list:
            return False
        return True

    def filter_size(self, args, size):
        # don't filter sync and open
        if size is None:
            return True
        if args.maxsize is not None and size > args.maxsize:
            return False
        if args.minsize is not None and size < args.minsize:
            return False
        return True

    def filter_latency(self, args, duration):
        if args.max is not None and (duration/1000) > args.max:
            return False
        if args.min is not None and (duration/1000) < args.min:
            return False
        return True

    def iotop_output_read(self, args):
        count = 0
        limit = args.top
        graph = Pyasciigraph()
        values = []
        for tid in sorted(self.state.tids.values(),
                          key=operator.attrgetter('read'), reverse=True):
            if not self.filter_process(args, tid):
                continue
            info_fmt = "{:>10} {:<25} {:>9} file {:>9} net {:>9} unknown"
            values.append((info_fmt.format(
                           convert_size(tid.read, padding_after=True),
                           "%s (%d)" % (tid.comm, tid.pid),
                           convert_size(tid.disk_read, padding_after=True),
                           convert_size(tid.net_read, padding_after=True),
                           convert_size(tid.unk_read, padding_after=True)),
                           tid.read))
            count = count + 1
            if limit > 0 and count >= limit:
                break
        for line in graph.graph('Per-process I/O Read', values,
                                with_value=False):
            print(line)

    def iotop_output_write(self, args):
        count = 0
        limit = args.top
        graph = Pyasciigraph()
        values = []
        for tid in sorted(self.state.tids.values(),
                          key=operator.attrgetter('write'), reverse=True):
            if not self.filter_process(args, tid):
                continue
            info_fmt = "{:>10} {:<25} {:>9} file {:>9} net {:>9} unknown "
            values.append((info_fmt.format(
                           convert_size(tid.write, padding_after=True),
                           "%s (%d)" % (tid.comm, tid.pid),
                           convert_size(tid.disk_write, padding_after=True),
                           convert_size(tid.net_write, padding_after=True),
                           convert_size(tid.unk_write, padding_after=True)),
                           tid.write))
            count = count + 1
            if limit > 0 and count >= limit:
                break
        for line in graph.graph('Per-process I/O Write', values,
                                with_value=False):
            print(line)

    def iotop_output_disk_read(self, args):
        count = 0
        limit = args.top
        graph = Pyasciigraph()
        values = []
        for tid in sorted(self.state.tids.values(),
                          key=operator.attrgetter('block_read'), reverse=True):
            if not self.filter_process(args, tid):
                continue
            if tid.block_read == 0:
                continue
            info_fmt = "{:>10} {:<22}"
            values.append((info_fmt.format(convert_size(tid.block_read,
                                           padding_after=True),
                                           "%s (pid=%d)" % (tid.comm,
                                                            tid.pid)),
                           tid.block_read))
            count = count + 1
            if limit > 0 and count >= limit:
                break
        for line in graph.graph('Block I/O Read', values, with_value=False):
            print(line)

    def iotop_output_disk_write(self, args):
        count = 0
        limit = args.top
        graph = Pyasciigraph()
        values = []
        for tid in sorted(self.state.tids.values(),
                          key=operator.attrgetter('block_write'),
                          reverse=True):
            if not self.filter_process(args, tid):
                continue
            if tid.block_write == 0:
                continue
            info_fmt = "{:>10} {:<22}"
            values.append((info_fmt.format(convert_size(tid.block_write,
                                           padding_after=True),
                                           "%s (pid=%d)" % (tid.comm,
                                                            tid.pid)),
                           tid.block_write))
            count = count + 1
            if limit > 0 and count >= limit:
                break
        for line in graph.graph('Block I/O Write', values, with_value=False):
            print(line)

    def iotop_output_nr_sector(self, args):
        graph = Pyasciigraph()
        values = []
        for disk in sorted(self.state.disks.values(),
                           key=operator.attrgetter('nr_sector'), reverse=True):
            if disk.nr_sector == 0:
                continue
            values.append((disk.prettyname, disk.nr_sector))
        for line in graph.graph('Disk nr_sector', values, unit=" sectors"):
            print(line)

    def iotop_output_nr_requests(self, args):
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

    def iotop_output_dev_latency(self, args):
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

    def iotop_output_net_recv_bytes(self, args):
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

    def iotop_output_net_sent_bytes(self, args):
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

    def iotop_output(self, args):
        self.iotop_output_read(args)
        self.iotop_output_write(args)
        self.iotop_output_file_read_write(args)
        self.iotop_output_disk_read(args)
        self.iotop_output_disk_write(args)
        self.iotop_output_nr_sector(args)
        self.iotop_output_nr_requests(args)
        self.iotop_output_dev_latency(args)
        self.iotop_output_net_recv_bytes(args)
        self.iotop_output_net_sent_bytes(args)
        self.output_latencies(args)

    def iolatency_freq_histogram(self, _min, _max, res, rq_list, title):
        step = (_max - _min) / res
        if step == 0:
            return
        buckets = []
        values = []
        graph = Pyasciigraph()
        for i in range(res):
            buckets.append(i * step)
            values.append(0)
        for i in rq_list:
            v = i / 1000
            b = min(int((v-_min)/step), res - 1)
            values[b] += 1
        g = []
        i = 0
        for v in values:
            g.append(("%0.03f" % (i * step + _min), v))
            i += 1
        for line in graph.graph(title, g, info_before=True):
            print(line)
        print("")

    def compute_disk_stats(self, dev, args):
        _max = 0
        _min = -1
        total = 0
        values = []
        count = len(dev.rq_list)
        if count == 0:
            return
        for rq in dev.rq_list:
            if rq.duration > _max:
                _max = rq.duration
            if _min == -1 or rq.duration < _min:
                _min = rq.duration
            total += rq.duration
            values.append(rq.duration)
        if count > 2:
            stdev = statistics.stdev(values) / 1000
        else:
            stdev = "?"
        dev.min = _min / 1000
        dev.max = _max / 1000
        dev.total = total / 1000
        dev.count = count
        dev.rq_values = values
        dev.stdev = stdev

    # iolatency functions
    def iolatency_output_disk(self, args):
        for dev in self.state.disks.keys():
            d = self.state.disks[dev]
            if d.max is None:
                self.compute_disk_stats(d, args)
            if d.count is not None:
                self.iolatency_freq_histogram(d.min, d.max,
                                              args.freq_resolution,
                                              d.rq_values,
                                              "Frequency distribution for "
                                              "disk %s (usec)" %
                                              (d.prettyname))

    def iolatency_output(self, args):
        self.iolatency_output_disk(args)

    def output_latencies(self, args):
        graph = Pyasciigraph()
        for proc in self.latency_hist.keys():
            values = []
            for v in self.latency_hist[proc]:
                values.append(("%s" % (v[0]), v[1]))
            for line in graph.graph('%s requests latency (ms)' % proc, values,
                                    unit=" ms"):
                print(line)

    def iostats_minmax(self, duration, current_min, current_max):
        _min = current_min
        _max = current_max
        if current_min is None or duration < current_min:
            _min = duration
        if duration > current_max:
            _max = duration
        return (_min, _max)

    def iostats_syscalls_line(self, fmt, name, count, _min, _max, total, rq):
        if count < 2:
            stdev = "?"
        else:
            stdev = "%0.03f" % (statistics.stdev(rq) / 1000)
        if count < 1:
            avg = "0.000"
        else:
            avg = "%0.03f" % (total / (count * 1000))
        if _min is None:
            _min = 0
        _min = "%0.03f" % (_min / 1000)
        _max = "%0.03f" % (_max / 1000)
        print(fmt.format(name, count, _min, avg, _max, stdev))

    def account_syscall_iorequests(self, args, s, iorequests):
        for rq in iorequests:
            if rq.iotype != IORequest.IO_SYSCALL:
                continue
            if not self.filter_size(args, rq.size):
                continue
            if not self.filter_latency(args, rq.duration):
                continue
            if rq.operation == IORequest.OP_READ:
                s.read_count += 1
                s.read_total += rq.duration
                s.read_rq.append(rq.duration)
                s.all_read.append(rq)
                s.read_min, s.read_max = self.iostats_minmax(
                    rq.duration, s.read_min, s.read_max)
            elif rq.operation == IORequest.OP_WRITE:
                s.write_count += 1
                s.write_total += rq.duration
                s.write_rq.append(rq.duration)
                s.all_write.append(rq)
                s.write_min, s.write_max = self.iostats_minmax(
                    rq.duration, s.write_min, s.write_max)
            elif rq.operation == IORequest.OP_SYNC:
                s.sync_count += 1
                s.sync_total += rq.duration
                s.sync_rq.append(rq.duration)
                s.all_sync.append(rq)
                s.sync_min, s.sync_max = self.iostats_minmax(
                    rq.duration, s.sync_min, s.sync_max)
            elif rq.operation == IORequest.OP_OPEN:
                s.open_count += 1
                s.open_total += rq.duration
                s.open_rq.append(rq.duration)
                s.all_open.append(rq)
                s.open_min, s.open_max = self.iostats_minmax(
                    rq.duration, s.open_min, s.open_max)

    def account_pending_syscalls(self, args, end_ns):
        pending_rq = []
        for tid in self.state.pending_syscalls:
            s = tid.current_syscall
            r = IORequest()
            r.name = s["name"]
            if r.name in SyscallConsts.OPEN_SYSCALLS:
                r.operation = IORequest.OP_OPEN
            elif r.name in SyscallConsts.READ_SYSCALLS:
                r.operation = IORequest.OP_READ
            elif r.name in SyscallConsts.WRITE_SYSCALLS:
                r.operation = IORequest.OP_WRITE
            elif r.name in SyscallConsts.SYNC_SYSCALLS:
                r.operation = IORequest.OP_SYNC
            else:
                continue
            r.iotype = IORequest.IO_SYSCALL
            r.begin = s["start"]
            r.duration = end_ns - s["start"]
            r.proc = tid
            r.pending = True
            pending_rq.append(r)
        return pending_rq

    def compute_syscalls_latency_stats(self, args, end_ns):
        s = Syscalls_stats()
        for tid in self.state.tids.values():
            if not self.filter_process(args, tid):
                continue
            self.account_syscall_iorequests(args, s, tid.iorequests)
            for fd in tid.fds.values():
                self.account_syscall_iorequests(args, s, fd.iorequests)
            for fd in tid.closed_fds.values():
                self.account_syscall_iorequests(args, s, fd.iorequests)
        r = self.account_pending_syscalls(args, end_ns)
        self.account_syscall_iorequests(args, s, r)
        return s

    def iostats_output_syscalls(self, args):
        s = self.syscalls_stats
        print("\nSyscalls latency statistics (usec):")
        fmt = "{:<14} {:>14} {:>14} {:>14} {:>14} {:>14}"
        print(fmt.format("Type", "Count", "Min", "Average",
                         "Max", "Stdev"))
        print("-" * 89)
        self.iostats_syscalls_line(fmt, "Open", s.open_count, s.open_min,
                                   s.open_max, s.open_total, s.open_rq)
        self.iostats_syscalls_line(fmt, "Read", s.read_count, s.read_min,
                                   s.read_max, s.read_total, s.read_rq)
        self.iostats_syscalls_line(fmt, "Write", s.write_count, s.write_min,
                                   s.write_max, s.write_total, s.write_rq)
        self.iostats_syscalls_line(fmt, "Sync", s.sync_count, s.sync_min,
                                   s.sync_max, s.sync_total, s.sync_rq)

    def iolatency_syscalls_output(self, args):
        s = self.syscalls_stats
        print("")
        if s.open_count > 0:
            self.iolatency_freq_histogram(s.open_min/1000, s.open_max/1000,
                                          args.freq_resolution, s.open_rq,
                                          "Open latency distribution (usec)")
        if s.read_count > 0:
            self.iolatency_freq_histogram(s.read_min/1000, s.read_max/1000,
                                          args.freq_resolution, s.read_rq,
                                          "Read latency distribution (usec)")
        if s.write_count > 0:
            self.iolatency_freq_histogram(s.write_min/1000, s.write_max/1000,
                                          args.freq_resolution, s.write_rq,
                                          "Write latency distribution (usec)")
        if s.sync_count > 0:
            self.iolatency_freq_histogram(s.sync_min/1000, s.sync_max/1000,
                                          args.freq_resolution, s.sync_rq,
                                          "Sync latency distribution (usec)")

    def iolatency_syscalls_list_output(self, args, title, rq_list,
                                       sortkey, reverse):
        limit = args.top
        count = 0
        if len(rq_list) == 0:
            return
        print(title)
        if args.extra:
            extra_fmt = "{:<48}"
            extra_title = "{:<8} {:<8} {:<8} {:<8} {:<8} {:<8} ".format(
                "Dirtied", "Alloc", "Free", "Written", "Kswap", "Cleared")
        else:
            extra_fmt = "{:<0}"
            extra_title = ""
        title_fmt = "{:<19} {:<20} {:<16} {:<23} {:<5} {:<24} {:<8} " + \
            extra_fmt + "{:<14}"
        fmt = "{:<40} {:<15} {:>16} {:>12}  {:<24} {:<8} " + \
            extra_fmt + "{:<14}"
        print(title_fmt.format("Begin", "End", "Name", "Duration (usec)",
                               "Size", "Proc", "PID", extra_title, "Filename"))
        for rq in sorted(rq_list,
                         key=operator.attrgetter(sortkey), reverse=reverse):
            # only limit the output if in the "top" view
            if reverse and count > limit:
                break
            if rq.size is None:
                size = "N/A"
            else:
                size = convert_size(rq.size)
            if args.extra:
                extra = "{:<8} {:<8} {:<8} {:<8} {:<8} {:<8} ".format(
                    rq.dirty, rq.page_alloc, rq.page_free, rq.page_written,
                    rq.woke_kswapd, rq.page_cleared)
            else:
                extra = ""
            name = rq.name.replace("syscall_entry_", "").replace("sys_", "")
            if rq.fd is None:
                filename = "None"
                fd = "None"
            else:
                filename = rq.fd.filename
                fd = rq.fd.fd
            if rq.pending:
                end = "??:??:??.?????????"
            else:
                end = ns_to_hour_nsec(rq.end, args.multi_day, args.gmt)
            print(fmt.format("[" + ns_to_hour_nsec(rq.begin, args.multi_day,
                                                   args.gmt) + "," + end + "]",
                             name,
                             "%0.03f" % (rq.duration/1000),
                             size, rq.proc.comm,
                             rq.proc.pid, extra,
                             "%s (fd=%s)" % (filename, fd)))
            count += 1

    def iolatency_syscalls_top_output(self, args):
        s = self.syscalls_stats
        self.iolatency_syscalls_list_output(
            args, "\nTop open syscall latencies (usec)", s.all_open,
            "duration", True)
        self.iolatency_syscalls_list_output(
            args, "\nTop read syscall latencies (usec)", s.all_read,
            "duration", True)
        self.iolatency_syscalls_list_output(
            args, "\nTop write syscall latencies (usec)", s.all_write,
            "duration", True)
        self.iolatency_syscalls_list_output(
            args, "\nTop sync syscall latencies (usec)", s.all_sync,
            "duration", True)

    def iolatency_syscalls_log_output(self, args):
        s = self.syscalls_stats
        self.iolatency_syscalls_list_output(
            args, "\nLog of all I/O system calls",
            s.all_open + s.all_read + s.all_write + s.all_sync,
            "begin", False)

    # iostats functions
    def iostats_output_disk(self, args):
        # TODO same with network
        if len(self.state.disks.keys()) == 0:
            return
        print("\nDisk latency statistics (usec):")
        fmt = "{:<14} {:>14} {:>14} {:>14} {:>14} {:>14}"
        print(fmt.format("Name", "Count", "Min", "Average", "Max", "Stdev"))
        print("-" * 89)

        for dev in self.state.disks.keys():
            d = self.state.disks[dev]
            if d.max is None:
                d = self.state.disks[dev]
            self.compute_disk_stats(d, args)
            if d.count is not None:
                self.iostats_syscalls_line(fmt, d.prettyname, d.count, d.min,
                                           d.max, d.total, d.rq_values)

    def iostats_output(self, args):
        self.iostats_output_syscalls(args)
        self.iostats_output_disk(args)

    def output(self, args, begin_ns, end_ns, final=0):
        print('%s to %s' % (ns_to_asctime(begin_ns), ns_to_asctime(end_ns)))
        self.iotop_output(args)
        self.syscalls_stats = self.compute_syscalls_latency_stats(args, end_ns)
        if args.stats:
            self.iostats_output(args)
            self.iolatency_syscalls_top_output(args)
        if args.freq:
            self.iolatency_syscalls_output(args)
            self.iolatency_output(args)
        if args.log:
            self.iolatency_syscalls_log_output(args)

    def reset_total(self, start_ts):
        for dev in self.state.disks.keys():
            self.state.disks[dev].init_counts()

        for iface in self.state.ifaces.keys():
            self.state.ifaces[iface].init_counts()

        for tid in self.state.tids.values():
            for fd in tid.fds.values():
                fd.init_counts()
            tid.init_counts()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='I/O usage analysis')
    parser.add_argument('path', metavar="<path/to/trace>", help='Trace path')
    parser.add_argument('-r', '--refresh', type=int,
                        help='Refresh period in seconds', default=0)
    parser.add_argument('--top', type=int, default=10,
                        help='Limit to top X TIDs (default = 10)')
    parser.add_argument('--name', type=str, default=0,
                        help='Filter the results only for this list of '
                             'process names')
    parser.add_argument('--pid', type=str, default=0,
                        help='Filter the results only for this list of PIDs')
    parser.add_argument('--latency', type=int, default=-1,
                        help='Only show I/O requests with a latency above '
                             'this threshold (ms)')
    parser.add_argument('--no-progress', action="store_true",
                        help='Don\'t display the progress bar')
    parser.add_argument('--gmt', action="store_true",
                        help='Manipulate timestamps based on GMT instead '
                        'of local time')
    parser.add_argument('--begin', type=str, help='start time')
    parser.add_argument('--end', type=str, help='end time')
    parser.add_argument('--seconds', action="store_true",
                        help='display time in seconds since epoch')
    parser.add_argument('--stats', action="store_true",
                        help='Display I/O and syscalls statistics')
    parser.add_argument('--log', action="store_true",
                        help='Display syscalls requests')
    parser.add_argument('--extra', action="store_true",
                        help='Display extra information in latency log/top')
    parser.add_argument('--freq', action="store_true",
                        help='Display frequency distribution of I/O '
                             'and syscalls')
    parser.add_argument('--freq-resolution', type=int, default=20,
                        help='Frequency distribution resolution (default 20)')
    parser.add_argument('--max', type=float, default=-1,
                        help='Filter out, operations longer than max usec')
    parser.add_argument('--min', type=float, default=-1,
                        help='Filter out, operations shorter than min usec')
    parser.add_argument('--maxsize', type=str, default=0,
                        help='Filter out, read/write operations working with '
                             'more than maxsize bytes')
    parser.add_argument('--minsize', type=str, default=0,
                        help='Filter out, read/write operations working with '
                             'less than minsize bytes')
    args = parser.parse_args()

    args.proc_list = None
    if args.name:
        args.proc_list = args.name.split(",")

    args.pid_filter_list = None
    if args.pid:
        args.pid_filter_list = args.pid.split(",")

    traces = TraceCollection()
    handle = traces.add_traces_recursive(args.path, "ctf")
    if handle is None:
        sys.exit(1)

    args.multi_day = is_multi_day_trace_collection(handle)
    if args.begin:
        args.begin = date_to_epoch_nsec(handle, args.begin, args.gmt)
    if args.end:
        args.end = date_to_epoch_nsec(handle, args.end, args.gmt)

    if args.max == -1:
        args.max = None
    if args.min == -1:
        args.min = None
    if args.maxsize:
        args.maxsize = str_to_bytes(args.maxsize)
    else:
        args.maxsize = None

    if args.minsize:
        args.minsize = str_to_bytes(args.minsize)
    else:
        args.minsize = None

    c = IOTop(traces)

    c.run(args)

    for h in handle.values():
        traces.remove_trace(h)
