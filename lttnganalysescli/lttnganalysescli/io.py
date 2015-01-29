from .command import Command
import lttnganalyses.syscalls
from linuxautomaton import common, sv
from ascii_graph import Pyasciigraph
import operator
import statistics


class IoAnalysis(Command):
    _VERSION = '0.1.0'
    _DESC = """The I/O command."""

    def __init__(self):
        super().__init__(self._add_arguments,
                         enable_proc_filter_args=True,
                         enable_max_min_args=True,
                         enable_max_min_size_arg=True,
                         enable_freq_arg=True,
                         enable_log_arg=True,
                         enable_stats_arg=True)

    def _validate_transform_args(self):
        self._arg_extra = self._args.extra

    def run(self):
        # parse arguments first
        self._parse_args()
        # validate, transform and save specific arguments
        self._validate_transform_args()
        # open the trace
        self._open_trace()
        # create the appropriate analysis/analyses
        self._create_analysis()
        # run the analysis
        self._run_analysis(self._reset_total, self._refresh)
        # process the results
        self._compute_stats()
        # print results
        self._print_results(self.start_ns, self.trace_end_ts, final=1)
        # close the trace
        self._close_trace()

    def _create_analysis(self):
        self._analysis = lttnganalyses.syscalls.SyscallsAnalysis(
            self._automaton.state)

    def _compute_stats(self):
        self.state = self._automaton.state
        pass

    def _refresh(self, begin, end):
        self._compute_stats()
        self._print_results(begin, end, final=0)
        self._reset_total(end)

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
            if not self.filter_process(tid):
                continue
            for fd in tid.fds.values():
                self.add_fd_dict(tid, fd, files)
            for fd in tid.closed_fds.values():
                self.add_fd_dict(tid, fd, files)
        return files

    # iotop functions
    def iotop_output_print_file_read(self, files):
        count = 0
        limit = self._arg_limit
        graph = Pyasciigraph()
        values = []
        sorted_f = sorted(files.items(), key=lambda files: files[1]['read'],
                          reverse=True)
        for f in sorted_f:
            if f[1]["read"] == 0:
                continue
            info_fmt = "{:>10}".format(common.convert_size(f[1]["read"],
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

    def iotop_output_print_file_write(self, files):
        # Compute files read
        count = 0
        limit = self._arg_limit
        graph = Pyasciigraph()
        values = []
        sorted_f = sorted(files.items(), key=lambda files: files[1]['write'],
                          reverse=True)
        for f in sorted_f:
            if f[1]["write"] == 0:
                continue
            info_fmt = "{:>10}".format(common.convert_size(f[1]["write"],
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

    def iotop_output_file_read_write(self):
        files = self.create_files_dict()
        self.iotop_output_print_file_read(files)
        self.iotop_output_print_file_write(files)

    def filter_process(self, proc):
        if self._arg_proc_list and proc.comm not in self._arg_proc_list:
            return False
        if self._arg_pid_list and str(proc.pid) not in self._arg_pid_list:
            return False
        return True

    def filter_size(self, size):
        # don't filter sync and open
        if size is None:
            return True
        if self._arg_maxsize is not None and size > self._arg_maxsize:
            return False
        if self._arg_minsize is not None and size < self._arg_minsize:
            return False
        return True

    def filter_latency(self, duration):
        if self._arg_max is not None and (duration/1000) > self._arg_max:
            return False
        if self._arg_min is not None and (duration/1000) < self._arg_min:
            return False
        return True

    def iotop_output_read(self):
        count = 0
        limit = self._arg_limit
        graph = Pyasciigraph()
        values = []
        for tid in sorted(self.state.tids.values(),
                          key=operator.attrgetter('read'), reverse=True):
            if not self.filter_process(tid):
                continue
            info_fmt = "{:>10} {:<25} {:>9} file {:>9} net {:>9} unknown"
            values.append((info_fmt.format(
                           common.convert_size(tid.read, padding_after=True),
                           "%s (%d)" % (tid.comm, tid.pid),
                           common.convert_size(tid.disk_read,
                                               padding_after=True),
                           common.convert_size(tid.net_read,
                                               padding_after=True),
                           common.convert_size(tid.unk_read,
                                               padding_after=True)),
                           tid.read))
            count = count + 1
            if limit > 0 and count >= limit:
                break
        for line in graph.graph('Per-process I/O Read', values,
                                with_value=False):
            print(line)

    def iotop_output_write(self):
        count = 0
        limit = self._arg_limit
        graph = Pyasciigraph()
        values = []
        for tid in sorted(self.state.tids.values(),
                          key=operator.attrgetter('write'), reverse=True):
            if not self.filter_process(tid):
                continue
            info_fmt = "{:>10} {:<25} {:>9} file {:>9} net {:>9} unknown "
            values.append((info_fmt.format(
                           common.convert_size(tid.write, padding_after=True),
                           "%s (%d)" % (tid.comm, tid.pid),
                           common.convert_size(tid.disk_write,
                                               padding_after=True),
                           common.convert_size(tid.net_write,
                                               padding_after=True),
                           common.convert_size(tid.unk_write,
                                               padding_after=True)),
                           tid.write))
            count = count + 1
            if limit > 0 and count >= limit:
                break
        for line in graph.graph('Per-process I/O Write', values,
                                with_value=False):
            print(line)

    def iotop_output_disk_read(self):
        count = 0
        limit = self._arg_limit
        graph = Pyasciigraph()
        values = []
        for tid in sorted(self.state.tids.values(),
                          key=operator.attrgetter('block_read'), reverse=True):
            if not self.filter_process(tid):
                continue
            if tid.block_read == 0:
                continue
            info_fmt = "{:>10} {:<22}"
            values.append((info_fmt.format(common.convert_size(tid.block_read,
                                           padding_after=True),
                                           "%s (pid=%d)" % (tid.comm,
                                                            tid.pid)),
                           tid.block_read))
            count = count + 1
            if limit > 0 and count >= limit:
                break
        for line in graph.graph('Block I/O Read', values, with_value=False):
            print(line)

    def iotop_output_disk_write(self):
        count = 0
        limit = self._arg_limit
        graph = Pyasciigraph()
        values = []
        for tid in sorted(self.state.tids.values(),
                          key=operator.attrgetter('block_write'),
                          reverse=True):
            if not self.filter_process(tid):
                continue
            if tid.block_write == 0:
                continue
            info_fmt = "{:>10} {:<22}"
            values.append((info_fmt.format(common.convert_size(tid.block_write,
                                           padding_after=True),
                                           "%s (pid=%d)" % (tid.comm,
                                                            tid.pid)),
                           tid.block_write))
            count = count + 1
            if limit > 0 and count >= limit:
                break
        for line in graph.graph('Block I/O Write', values, with_value=False):
            print(line)

    def iotop_output_nr_sector(self):
        graph = Pyasciigraph()
        values = []
        for disk in sorted(self.state.disks.values(),
                           key=operator.attrgetter('nr_sector'), reverse=True):
            if disk.nr_sector == 0:
                continue
            values.append((disk.prettyname, disk.nr_sector))
        for line in graph.graph('Disk nr_sector', values, unit=" sectors"):
            print(line)

    def iotop_output_nr_requests(self):
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

    def iotop_output_dev_latency(self):
        graph = Pyasciigraph()
        values = []
        for disk in self.state.disks.values():
            if disk.completed_requests == 0:
                continue
            total = (disk.request_time / disk.completed_requests) \
                / common.MSEC_PER_NSEC
            total = float("%0.03f" % total)
            values.append(("%s" % disk.prettyname, total))
        for line in graph.graph('Disk request time/sector', values, sort=2,
                                unit=" ms"):
            print(line)

    def iotop_output_net_recv_bytes(self):
        graph = Pyasciigraph()
        values = []
        for iface in sorted(self.state.ifaces.values(),
                            key=operator.attrgetter('recv_bytes'),
                            reverse=True):
            values.append(("%s %s" % (common.convert_size(iface.recv_bytes),
                                      iface.name),
                          iface.recv_bytes))
        for line in graph.graph('Network recv_bytes', values,
                                with_value=False):
            print(line)

    def iotop_output_net_sent_bytes(self):
        graph = Pyasciigraph()
        values = []
        for iface in sorted(self.state.ifaces.values(),
                            key=operator.attrgetter('send_bytes'),
                            reverse=True):
            values.append(("%s %s" % (common.convert_size(iface.send_bytes),
                                      iface.name),
                          iface.send_bytes))
        for line in graph.graph('Network sent_bytes', values,
                                with_value=False):
            print(line)

    def iotop_output(self):
        self.iotop_output_read()
        self.iotop_output_write()
        self.iotop_output_file_read_write()
        self.iotop_output_disk_read()
        self.iotop_output_disk_write()
        self.iotop_output_nr_sector()
        self.iotop_output_nr_requests()
        self.iotop_output_dev_latency()
        self.iotop_output_net_recv_bytes()
        self.iotop_output_net_sent_bytes()
#        self.output_latencies()

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

    def compute_disk_stats(self, dev):
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
    def iolatency_output_disk(self):
        for dev in self.state.disks.keys():
            d = self.state.disks[dev]
            if d.max is None:
                self.compute_disk_stats(d)
            if d.count is not None:
                self.iolatency_freq_histogram(d.min, d.max,
                                              self._arg_freq_resolution,
                                              d.rq_values,
                                              "Frequency distribution for "
                                              "disk %s (usec)" %
                                              (d.prettyname))

    def iolatency_output(self):
        self.iolatency_output_disk()

#    def output_latencies(self):
#        graph = Pyasciigraph()
#        for proc in self.latency_hist.keys():
#            values = []
#            for v in self.latency_hist[proc]:
#                values.append(("%s" % (v[0]), v[1]))
#            for line in graph.graph('%s requests latency (ms)' % proc, values,
#                                    unit=" ms"):
#                print(line)

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

    def account_syscall_iorequests(self, s, iorequests):
        for rq in iorequests:
            # filter out if completely out of range but accept the
            # union to show the real begin/end time
            if self._arg_begin and self._arg_end and rq.end and \
                    rq.begin > self._arg_end:
                continue
            if rq.iotype != sv.IORequest.IO_SYSCALL:
                continue
            if not self.filter_size(rq.size):
                continue
            if not self.filter_latency(rq.duration):
                continue
            if rq.operation == sv.IORequest.OP_READ:
                s.read_count += 1
                s.read_total += rq.duration
                s.read_rq.append(rq.duration)
                s.all_read.append(rq)
                s.read_min, s.read_max = self.iostats_minmax(
                    rq.duration, s.read_min, s.read_max)
            elif rq.operation == sv.IORequest.OP_WRITE:
                s.write_count += 1
                s.write_total += rq.duration
                s.write_rq.append(rq.duration)
                s.all_write.append(rq)
                s.write_min, s.write_max = self.iostats_minmax(
                    rq.duration, s.write_min, s.write_max)
            elif rq.operation == sv.IORequest.OP_SYNC:
                s.sync_count += 1
                s.sync_total += rq.duration
                s.sync_rq.append(rq.duration)
                s.all_sync.append(rq)
                s.sync_min, s.sync_max = self.iostats_minmax(
                    rq.duration, s.sync_min, s.sync_max)
            elif rq.operation == sv.IORequest.OP_OPEN:
                s.open_count += 1
                s.open_total += rq.duration
                s.open_rq.append(rq.duration)
                s.all_open.append(rq)
                s.open_min, s.open_max = self.iostats_minmax(
                    rq.duration, s.open_min, s.open_max)

    def compute_syscalls_latency_stats(self, end_ns):
        s = sv.Syscalls_stats()
        for tid in self.state.tids.values():
            if not self.filter_process(tid):
                continue
            self.account_syscall_iorequests(s, tid.iorequests)
            for fd in tid.fds.values():
                self.account_syscall_iorequests(s, fd.iorequests)
            for fd in tid.closed_fds.values():
                self.account_syscall_iorequests(s, fd.iorequests)
        return s

    def iostats_output_syscalls(self):
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

    def iolatency_syscalls_output(self):
        s = self.syscalls_stats
        print("")
        if s.open_count > 0:
            self.iolatency_freq_histogram(s.open_min/1000, s.open_max/1000,
                                          self._arg_freq_resolution, s.open_rq,
                                          "Open latency distribution (usec)")
        if s.read_count > 0:
            self.iolatency_freq_histogram(s.read_min/1000, s.read_max/1000,
                                          self._arg_freq_resolution, s.read_rq,
                                          "Read latency distribution (usec)")
        if s.write_count > 0:
            self.iolatency_freq_histogram(s.write_min/1000, s.write_max/1000,
                                          self._arg_freq_resolution,
                                          s.write_rq,
                                          "Write latency distribution (usec)")
        if s.sync_count > 0:
            self.iolatency_freq_histogram(s.sync_min/1000, s.sync_max/1000,
                                          self._arg_freq_resolution, s.sync_rq,
                                          "Sync latency distribution (usec)")

    def iolatency_syscalls_list_output(self, title, rq_list,
                                       sortkey, reverse):
        limit = self._arg_limit
        count = 0
        outrange_legend = False
        if len(rq_list) == 0:
            return
        print(title)
        if self._arg_extra:
            extra_fmt = "{:<48}"
            extra_title = "{:<8} {:<8} {:<8} {:<8} {:<8} {:<8} ".format(
                "Dirtied", "Alloc", "Free", "Written", "Kswap", "Cleared")
        else:
            extra_fmt = "{:<0}"
            extra_title = ""
        title_fmt = "{:<19} {:<20} {:<16} {:<23} {:<5} {:<24} {:<8} " + \
            extra_fmt + "{:<14}"
        fmt = "{:<40} {:<16} {:>16} {:>12}  {:<24} {:<8} " + \
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
                size = common.convert_size(rq.size)
            if self._arg_extra:
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
            end = common.ns_to_hour_nsec(rq.end, self._arg_multi_day,
                                         self._arg_gmt)

            outrange = " "
            duration = rq.duration
            if self._arg_begin and rq.begin < self._arg_begin:
                outrange = "*"
                outrange_legend = True
            if self._arg_end and rq.end > self._arg_end:
                outrange = "*"
                outrange_legend = True

            print(fmt.format("[" + common.ns_to_hour_nsec(
                rq.begin, self._arg_multi_day, self._arg_gmt) + "," +
                end + "]" + outrange,
                name,
                "%0.03f" % (duration/1000) + outrange,
                size, rq.proc.comm,
                rq.proc.pid, extra,
                "%s (fd=%s)" % (filename, fd)))
            count += 1
        if outrange_legend:
            print("*: Syscalls started and/or completed outside of the "
                  "range specified")

    def iolatency_syscalls_top_output(self):
        s = self.syscalls_stats
        self.iolatency_syscalls_list_output(
            "\nTop open syscall latencies (usec)", s.all_open,
            "duration", True)
        self.iolatency_syscalls_list_output(
            "\nTop read syscall latencies (usec)", s.all_read,
            "duration", True)
        self.iolatency_syscalls_list_output(
            "\nTop write syscall latencies (usec)", s.all_write,
            "duration", True)
        self.iolatency_syscalls_list_output(
            "\nTop sync syscall latencies (usec)", s.all_sync,
            "duration", True)

    def iolatency_syscalls_log_output(self):
        s = self.syscalls_stats
        self.iolatency_syscalls_list_output(
            "\nLog of all I/O system calls",
            s.all_open + s.all_read + s.all_write + s.all_sync,
            "begin", False)

    # iostats functions
    def iostats_output_disk(self):
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
            self.compute_disk_stats(d)
            if d.count is not None:
                self.iostats_syscalls_line(fmt, d.prettyname, d.count, d.min,
                                           d.max, d.total, d.rq_values)

    def iostats_output(self):
        self.iostats_output_syscalls()
        self.iostats_output_disk()

    def _print_results(self, begin_ns, end_ns, final=0):
        print('%s to %s' % (common.ns_to_asctime(begin_ns),
                            common.ns_to_asctime(end_ns)))
        self.iotop_output()
        self.syscalls_stats = self.compute_syscalls_latency_stats(end_ns)
        if self._arg_stats:
            self.iostats_output()
            self.iolatency_syscalls_top_output()
        if self._arg_freq:
            self.iolatency_syscalls_output()
            self.iolatency_output()
        if self._arg_log:
            self.iolatency_syscalls_log_output()

    def _reset_total(self, start_ts):
        for dev in self.state.disks.keys():
            self.state.disks[dev].init_counts()

        for iface in self.state.ifaces.keys():
            self.state.ifaces[iface].init_counts()

        for tid in self.state.tids.values():
            for fd in tid.fds.values():
                fd.init_counts()
            for fd in tid.closed_fds.values():
                fd.init_counts()
            tid.init_counts()

    def _add_arguments(self, ap):
        ap.add_argument('--extra', type=str, default=0,
                        help='Show extra information in stats (beta)')
        # specific argument
        pass


# entry point
def run():
    # create command
    iocmd = IoAnalysis()

    # execute command
    iocmd.run()
