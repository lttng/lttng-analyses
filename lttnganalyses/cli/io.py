# The MIT License (MIT)
#
# Copyright (C) 2015 - Julien Desfossez <jdesfossez@efficios.com>
#               2015 - Antoine Busque <abusque@efficios.com>
#               2015 - Philippe Proulx <pproulx@efficios.com>
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
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import collections
import operator
import statistics
import sys
from . import mi
from . import termgraph
from ..core import io
from ..common import format_utils
from .command import Command
from ..linuxautomaton import common


_UsageTables = collections.namedtuple('_UsageTables', [
    'per_proc_read',
    'per_proc_write',
    'per_file_read',
    'per_file_write',
    'per_proc_block_read',
    'per_proc_block_write',
    'per_disk_sector',
    'per_disk_request',
    'per_disk_rtps',
    'per_netif_recv',
    'per_netif_send',
])


class IoAnalysisCommand(Command):
    _DESC = """The I/O command."""
    _ANALYSIS_CLASS = io.IoAnalysis
    _MI_TITLE = 'I/O analysis'
    _MI_DESCRIPTION = 'System call/disk latency statistics, system call ' + \
                      'latency distribution, system call top latencies, ' + \
                      'I/O usage top, and I/O operations log'
    _MI_TAGS = [
        mi.Tags.IO,
        mi.Tags.SYSCALL,
        mi.Tags.STATS,
        mi.Tags.FREQ,
        mi.Tags.LOG,
        mi.Tags.TOP,
    ]
    _MI_TABLE_CLASS_SYSCALL_LATENCY_STATS = 'syscall-latency-stats'
    _MI_TABLE_CLASS_PART_LATENCY_STATS = 'disk-latency-stats'
    _MI_TABLE_CLASS_FREQ = 'freq'
    _MI_TABLE_CLASS_TOP_SYSCALL = 'top-syscall'
    _MI_TABLE_CLASS_LOG = 'log'
    _MI_TABLE_CLASS_PER_PROCESS_TOP = 'per-process-top'
    _MI_TABLE_CLASS_PER_FILE_TOP = 'per-file-top'
    _MI_TABLE_CLASS_PER_PROCESS_TOP_BLOCK = 'per-process-top-block'
    _MI_TABLE_CLASS_PER_DISK_TOP_SECTOR = 'per-disk-top-sector'
    _MI_TABLE_CLASS_PER_DISK_TOP_REQUEST = 'per-disk-top-request'
    _MI_TABLE_CLASS_PER_DISK_TOP_RTPS = 'per-disk-top-rps'
    _MI_TABLE_CLASS_PER_NETIF_TOP = 'per-netif-top'
    _MI_TABLE_CLASSES = [
        (
            _MI_TABLE_CLASS_SYSCALL_LATENCY_STATS,
            'System call latency statistics', [
                ('obj', 'System call category', mi.String),
                ('count', 'Call count', mi.Integer, 'calls'),
                ('min_latency', 'Minimum call latency', mi.Duration),
                ('avg_latency', 'Average call latency', mi.Duration),
                ('max_latency', 'Maximum call latency', mi.Duration),
                ('stdev_latency', 'System call latency standard deviation',
                 mi.Duration),
            ]
        ),
        (
            _MI_TABLE_CLASS_PART_LATENCY_STATS,
            'Partition latency statistics', [
                ('obj', 'Partition', mi.Disk),
                ('count', 'Access count', mi.Integer, 'accesses'),
                ('min_latency', 'Minimum access latency', mi.Duration),
                ('avg_latency', 'Average access latency', mi.Duration),
                ('max_latency', 'Maximum access latency', mi.Duration),
                ('stdev_latency', 'System access latency standard deviation',
                 mi.Duration),
            ]
        ),
        (
            _MI_TABLE_CLASS_FREQ,
            'I/O request latency distribution', [
                ('latency_lower', 'Latency (lower bound)', mi.Duration),
                ('latency_upper', 'Latency (upper bound)', mi.Duration),
                ('count', 'Request count', mi.Integer, 'requests'),
            ]
        ),
        (
            _MI_TABLE_CLASS_TOP_SYSCALL,
            'Top system call latencies', [
                ('time_range', 'Call time range', mi.TimeRange),
                ('out_of_range', 'System call out of range?', mi.Boolean),
                ('duration', 'Call duration', mi.Duration),
                ('syscall', 'System call', mi.Syscall),
                ('size', 'Read/write size', mi.Size),
                ('process', 'Process', mi.Process),
                ('path', 'File path', mi.Path),
                ('fd', 'File descriptor', mi.Fd),
            ]
        ),
        (
            _MI_TABLE_CLASS_LOG,
            'I/O operations log', [
                ('time_range', 'Call time range', mi.TimeRange),
                ('out_of_range', 'System call out of range?', mi.Boolean),
                ('duration', 'Call duration', mi.Duration),
                ('syscall', 'System call', mi.Syscall),
                ('size', 'Read/write size', mi.Size),
                ('process', 'Process', mi.Process),
                ('path', 'File path', mi.Path),
                ('fd', 'File descriptor', mi.Fd),
            ]
        ),
        (
            _MI_TABLE_CLASS_PER_PROCESS_TOP,
            'Per-process top I/O operations', [
                ('process', 'Process', mi.Process),
                ('size', 'Total operations size', mi.Size),
                ('disk_size', 'Disk operations size', mi.Size),
                ('net_size', 'Network operations size', mi.Size),
                ('unknown_size', 'Unknown operations size', mi.Size),
            ]
        ),
        (
            _MI_TABLE_CLASS_PER_FILE_TOP,
            'Per-file top I/O operations', [
                ('path', 'File path/info', mi.Path),
                ('size', 'Operations size', mi.Size),
                ('fd_owners', 'File descriptor owners', mi.String),
            ]
        ),
        (
            _MI_TABLE_CLASS_PER_PROCESS_TOP_BLOCK,
            'Per-process top block I/O operations', [
                ('process', 'Process', mi.Process),
                ('size', 'Operations size', mi.Size),
            ]
        ),
        (
            _MI_TABLE_CLASS_PER_DISK_TOP_SECTOR,
            'Per-disk top sector I/O operations', [
                ('disk', 'Disk', mi.Disk),
                ('count', 'Sector count', mi.Integer, 'sectors'),
            ]
        ),
        (
            _MI_TABLE_CLASS_PER_DISK_TOP_REQUEST,
            'Per-disk top I/O requests', [
                ('disk', 'Disk', mi.Disk),
                ('count', 'Request count', mi.Integer, 'I/O requests'),
            ]
        ),
        (
            _MI_TABLE_CLASS_PER_DISK_TOP_RTPS,
            'Per-disk top I/O request time/sector', [
                ('disk', 'Disk', mi.Disk),
                ('rtps', 'Request time/sector', mi.Duration),
            ]
        ),
        (
            _MI_TABLE_CLASS_PER_NETIF_TOP,
            'Per-network interface top I/O operations', [
                ('netif', 'Network interface', mi.NetIf),
                ('size', 'Operations size', mi.Size),
            ]
        ),
    ]
    _LATENCY_STATS_FORMAT = '{:<14} {:>14} {:>14} {:>14} {:>14} {:>14}'
    _SECTION_SEPARATOR_STRING = '-' * 89

    def _analysis_tick(self, begin_ns, end_ns):
        syscall_latency_stats_table = None
        disk_latency_stats_table = None
        freq_tables = None
        top_tables = None
        log_table = None
        usage_tables = None

        if self._args.stats:
            syscall_latency_stats_table, disk_latency_stats_table = \
                self._get_latency_stats_result_tables(begin_ns, end_ns)

        if self._args.freq:
            freq_tables = self._get_freq_result_tables(begin_ns, end_ns)

        if self._args.usage:
            usage_tables = self._get_usage_result_tables(begin_ns, end_ns)

        if self._args.top:
            top_tables = self._get_top_result_tables(begin_ns, end_ns)

        if self._args.log:
            log_table = self._get_log_result_table(begin_ns, end_ns)

        if self._mi_mode:
            self._mi_append_result_tables([
                log_table,
                syscall_latency_stats_table,
                disk_latency_stats_table,
            ])
            self._mi_append_result_tables(top_tables)
            self._mi_append_result_tables(usage_tables)
            self._mi_append_result_tables(freq_tables)
        else:
            self._print_date(begin_ns, end_ns)

            if self._args.usage:
                self._print_usage(usage_tables)

            if self._args.stats:
                self._print_latency_stats(syscall_latency_stats_table,
                                          disk_latency_stats_table)

            if self._args.top:
                self._print_top(top_tables)

            if self._args.freq:
                self._print_freq(freq_tables)

            if self._args.log:
                self._print_log(log_table)

    def _create_summary_result_tables(self):
        # TODO: create a summary table here
        self._mi_clear_result_tables()

    # Filter predicates
    def _filter_size(self, size):
        if size is None:
            return True
        if self._args.maxsize is not None and size > self._args.maxsize:
            return False
        if self._args.minsize is not None and size < self._args.minsize:
            return False
        return True

    def _filter_latency(self, duration):
        if self._args.max is not None and duration > self._args.max:
            return False
        if self._args.min is not None and duration < self._args.min:
            return False
        return True

    def _filter_time_range(self, begin, end):
        # Note: we only want to return False only when a request has
        # ended and is completely outside the timerange (i.e. begun
        # after the end of the time range).
        return not (self._args.begin and self._args.end and end and
                    begin > self._args.end)

    def _filter_io_request(self, io_rq):
        return self._filter_size(io_rq.size) and \
            self._filter_latency(io_rq.duration) and \
            self._filter_time_range(io_rq.begin_ts, io_rq.end_ts)

    def _is_io_rq_out_of_range(self, io_rq):
        return self._args.begin and io_rq.begin_ts < self._args.begin or \
            self._args.end and io_rq.end_ts > self._args.end

    def _append_per_proc_read_usage_row(self, proc_stats, result_table):
        result_table.append_row(
            process=mi.Process(proc_stats.comm, pid=proc_stats.pid,
                               tid=proc_stats.tid),
            size=mi.Size(proc_stats.total_read),
            disk_size=mi.Size(proc_stats.disk_io.read),
            net_size=mi.Size(proc_stats.net_io.read),
            unknown_size=mi.Size(proc_stats.unk_io.read),
        )

        return True

    def _append_per_proc_write_usage_row(self, proc_stats, result_table):
        result_table.append_row(
            process=mi.Process(proc_stats.comm, pid=proc_stats.pid,
                               tid=proc_stats.tid),
            size=mi.Size(proc_stats.total_write),
            disk_size=mi.Size(proc_stats.disk_io.write),
            net_size=mi.Size(proc_stats.net_io.write),
            unknown_size=mi.Size(proc_stats.unk_io.write),
        )

        return True

    def _append_per_proc_block_read_usage_row(self, proc_stats, result_table):
        if proc_stats.block_io.read == 0:
            return False

        if proc_stats.comm:
            proc_name = proc_stats.comm
        else:
            proc_name = None

        result_table.append_row(
            process=mi.Process(proc_name, pid=proc_stats.pid,
                               tid=proc_stats.tid),
            size=mi.Size(proc_stats.block_io.read),
        )

        return True

    def _append_per_proc_block_write_usage_row(self, proc_stats, result_table):
        if proc_stats.block_io.write == 0:
            return False

        if proc_stats.comm:
            proc_name = proc_stats.comm
        else:
            proc_name = None

        result_table.append_row(
            process=mi.Process(proc_name, pid=proc_stats.pid,
                               tid=proc_stats.tid),
            size=mi.Size(proc_stats.block_io.write),
        )

        return True

    def _append_disk_sector_usage_row(self, disk_stats, result_table):
        if disk_stats.total_rq_sectors == 0:
            return None

        result_table.append_row(
            disk=mi.Disk(disk_stats.disk_name),
            count=mi.Integer(disk_stats.total_rq_sectors),
        )

        return True

    def _append_disk_request_usage_row(self, disk_stats, result_table):
        if disk_stats.rq_count == 0:
            return False

        result_table.append_row(
            disk=mi.Disk(disk_stats.disk_name),
            count=mi.Integer(disk_stats.rq_count),
        )

        return True

    def _append_disk_rtps_usage_row(self, disk_stats, result_table):
        if disk_stats.rq_count == 0:
            return False

        avg_latency = (disk_stats.total_rq_duration / disk_stats.rq_count)
        result_table.append_row(
            disk=mi.Disk(disk_stats.disk_name),
            rtps=mi.Duration(avg_latency),
        )

        return True

    def _append_netif_recv_usage_row(self, netif_stats, result_table):
        result_table.append_row(
            netif=mi.NetIf(netif_stats.name),
            size=mi.Size(netif_stats.recv_bytes)
        )

        return True

    def _append_netif_send_usage_row(self, netif_stats, result_table):
        result_table.append_row(
            netif=mi.NetIf(netif_stats.name),
            size=mi.Size(netif_stats.sent_bytes)
        )

        return True

    def _get_file_stats_fd_owners_str(self, file_stats):
        fd_by_pid_str = ''

        for pid, fd in file_stats.fd_by_pid.items():
            comm = self._analysis.tids[pid].comm
            fd_by_pid_str += 'fd %d in %s (%s) ' % (fd, comm, pid)

        return fd_by_pid_str

    def _append_file_read_usage_row(self, file_stats, result_table):
        if file_stats.io.read == 0:
            return False

        fd_owners = self._get_file_stats_fd_owners_str(file_stats)
        result_table.append_row(
            path=mi.Path(file_stats.filename),
            size=mi.Size(file_stats.io.read),
            fd_owners=mi.String(fd_owners),
        )

        return True

    def _append_file_write_usage_row(self, file_stats, result_table):
        if file_stats.io.write == 0:
            return False

        fd_owners = self._get_file_stats_fd_owners_str(file_stats)
        result_table.append_row(
            path=mi.Path(file_stats.filename),
            size=mi.Size(file_stats.io.write),
            fd_owners=mi.String(fd_owners),
        )

        return True

    def _fill_usage_result_table(self, input_list, append_row_cb,
                                 result_table):
        count = 0
        limit = self._args.limit

        for elem in input_list:
            if append_row_cb(elem, result_table):
                count += 1

                if limit is not None and count >= limit:
                    break

    def _fill_per_process_read_usage_result_table(self, result_table):
        input_list = sorted(self._analysis.tids.values(),
                            key=operator.attrgetter('total_read'),
                            reverse=True)
        self._fill_usage_result_table(input_list,
                                      self._append_per_proc_read_usage_row,
                                      result_table)

    def _fill_per_process_write_usage_result_table(self, result_table):
        input_list = sorted(self._analysis.tids.values(),
                            key=operator.attrgetter('total_write'),
                            reverse=True)
        self._fill_usage_result_table(input_list,
                                      self._append_per_proc_write_usage_row,
                                      result_table)

    def _fill_per_process_block_read_usage_result_table(self, result_table):
        input_list = sorted(self._analysis.tids.values(),
                            key=operator.attrgetter('block_io.read'),
                            reverse=True)
        self._fill_usage_result_table(
            input_list, self._append_per_proc_block_read_usage_row,
            result_table)

    def _fill_per_process_block_write_usage_result_table(self, result_table):
        input_list = sorted(self._analysis.tids.values(),
                            key=operator.attrgetter('block_io.write'),
                            reverse=True)
        self._fill_usage_result_table(
            input_list, self._append_per_proc_block_write_usage_row,
            result_table)

    def _fill_disk_sector_usage_result_table(self, result_table):
        input_list = sorted(self._analysis.disks.values(),
                            key=operator.attrgetter('total_rq_sectors'),
                            reverse=True)
        self._fill_usage_result_table(input_list,
                                      self._append_disk_sector_usage_row,
                                      result_table)

    def _fill_disk_request_usage_result_table(self, result_table):
        input_list = sorted(self._analysis.disks.values(),
                            key=operator.attrgetter('rq_count'),
                            reverse=True)
        self._fill_usage_result_table(input_list,
                                      self._append_disk_request_usage_row,
                                      result_table)

    def _fill_disk_rtps_usage_result_table(self, result_table):
        input_list = self._analysis.disks.values()
        self._fill_usage_result_table(input_list,
                                      self._append_disk_rtps_usage_row,
                                      result_table)

    def _fill_netif_recv_usage_result_table(self, result_table):
        input_list = sorted(self._analysis.ifaces.values(),
                            key=operator.attrgetter('recv_bytes'),
                            reverse=True)
        self._fill_usage_result_table(input_list,
                                      self._append_netif_recv_usage_row,
                                      result_table)

    def _fill_netif_send_usage_result_table(self, result_table):
        input_list = sorted(self._analysis.ifaces.values(),
                            key=operator.attrgetter('sent_bytes'),
                            reverse=True)
        self._fill_usage_result_table(input_list,
                                      self._append_netif_send_usage_row,
                                      result_table)

    def _fill_file_read_usage_result_table(self, files, result_table):
        input_list = sorted(files.values(),
                            key=lambda file_stats: file_stats.io.read,
                            reverse=True)
        self._fill_usage_result_table(input_list,
                                      self._append_file_read_usage_row,
                                      result_table)

    def _fill_file_write_usage_result_table(self, files, result_table):
        input_list = sorted(files.values(),
                            key=lambda file_stats: file_stats.io.write,
                            reverse=True)
        self._fill_usage_result_table(input_list,
                                      self._append_file_write_usage_row,
                                      result_table)

    def _fill_file_usage_result_tables(self, read_table, write_table):
        files = self._analysis.get_files_stats()
        self._fill_file_read_usage_result_table(files, read_table)
        self._fill_file_write_usage_result_table(files, write_table)

    def _get_usage_result_tables(self, begin, end):
        # create result tables
        per_proc_read_table = self._mi_create_result_table(
            self._MI_TABLE_CLASS_PER_PROCESS_TOP, begin, end, 'read')
        per_proc_write_table = self._mi_create_result_table(
            self._MI_TABLE_CLASS_PER_PROCESS_TOP, begin, end, 'written')
        per_file_read_table = self._mi_create_result_table(
            self._MI_TABLE_CLASS_PER_FILE_TOP, begin, end, 'read')
        per_file_write_table = self._mi_create_result_table(
            self._MI_TABLE_CLASS_PER_FILE_TOP, begin, end, 'written')
        per_proc_block_read_table = self._mi_create_result_table(
            self._MI_TABLE_CLASS_PER_PROCESS_TOP_BLOCK, begin, end, 'read')
        per_proc_block_write_table = self._mi_create_result_table(
            self._MI_TABLE_CLASS_PER_PROCESS_TOP_BLOCK, begin, end, 'written')
        per_disk_sector_table = self._mi_create_result_table(
            self._MI_TABLE_CLASS_PER_DISK_TOP_SECTOR, begin, end)
        per_disk_request_table = self._mi_create_result_table(
            self._MI_TABLE_CLASS_PER_DISK_TOP_REQUEST, begin, end)
        per_disk_rtps_table = self._mi_create_result_table(
            self._MI_TABLE_CLASS_PER_DISK_TOP_RTPS, begin, end)
        per_netif_recv_table = self._mi_create_result_table(
            self._MI_TABLE_CLASS_PER_NETIF_TOP, begin, end, 'received')
        per_netif_send_table = self._mi_create_result_table(
            self._MI_TABLE_CLASS_PER_NETIF_TOP, begin, end, 'sent')

        # fill result tables
        self._fill_per_process_read_usage_result_table(per_proc_read_table)
        self._fill_per_process_write_usage_result_table(per_proc_write_table)
        self._fill_file_usage_result_tables(per_file_read_table,
                                            per_file_write_table)
        self._fill_per_process_block_read_usage_result_table(
            per_proc_block_read_table)
        self._fill_per_process_block_write_usage_result_table(
            per_proc_block_write_table)
        self._fill_disk_sector_usage_result_table(per_disk_sector_table)
        self._fill_disk_request_usage_result_table(per_disk_request_table)
        self._fill_disk_rtps_usage_result_table(per_disk_rtps_table)
        self._fill_netif_recv_usage_result_table(per_netif_recv_table)
        self._fill_netif_send_usage_result_table(per_netif_send_table)

        return _UsageTables(
            per_proc_read=per_proc_read_table,
            per_proc_write=per_proc_write_table,
            per_file_read=per_file_read_table,
            per_file_write=per_file_write_table,
            per_proc_block_read=per_proc_block_read_table,
            per_proc_block_write=per_proc_block_write_table,
            per_disk_sector=per_disk_sector_table,
            per_disk_request=per_disk_request_table,
            per_disk_rtps=per_disk_rtps_table,
            per_netif_recv=per_netif_recv_table,
            per_netif_send=per_netif_send_table,
        )

    def _print_per_proc_io(self, result_table, title):
        header_format = '{:<25} {:<10} {:<10} {:<10}'
        label_header = header_format.format(
            'Process', 'Disk', 'Net', 'Unknown'
        )

        def get_label(row):
            label_format = '{:<25} {:>10} {:>10} {:>10}'
            if row.process.pid is None:
                pid_str = 'unknown (tid=%d)' % (row.process.tid)
            else:
                pid_str = str(row.process.pid)

            label = label_format.format(
                '%s (%s)' % (row.process.name, pid_str),
                format_utils.format_size(row.disk_size.value),
                format_utils.format_size(row.net_size.value),
                format_utils.format_size(row.unknown_size.value)
            )

            return label

        graph = termgraph.BarGraph(
            title='Per-process I/O ' + title,
            label_header=label_header,
            get_value=lambda row: row.size.value,
            get_value_str=format_utils.format_size,
            get_label=get_label,
            data=result_table.rows
        )

        graph.print_graph()

    def _print_per_proc_block_io(self, result_table, title):
        def get_label(row):
            proc_name = row.process.name

            if not proc_name:
                proc_name = 'unknown'

            if row.process.pid is None:
                pid_str = 'unknown (tid={})'.format(row.process.tid)
            else:
                pid_str = str(row.process.pid)

            return '{} (pid={})'.format(proc_name, pid_str)

        graph = termgraph.BarGraph(
            title='Block I/O ' + title,
            label_header='Process',
            get_value=lambda row: row.size.value,
            get_value_str=format_utils.format_size,
            get_label=get_label,
            data=result_table.rows
        )

        graph.print_graph()

    def _print_per_disk_sector(self, result_table):
        graph = termgraph.BarGraph(
            title='Disk Requests Sector Count',
            label_header='Disk',
            unit='sectors',
            get_value=lambda row: row.count.value,
            get_label=lambda row: row.disk.name,
            data=result_table.rows
        )

        graph.print_graph()

    def _print_per_disk_request(self, result_table):
        graph = termgraph.BarGraph(
            title='Disk Request Count',
            label_header='Disk',
            unit='requests',
            get_value=lambda row: row.count.value,
            get_label=lambda row: row.disk.name,
            data=result_table.rows
        )

        graph.print_graph()

    def _print_per_disk_rtps(self, result_table):
        graph = termgraph.BarGraph(
            title='Disk Request Average Latency',
            label_header='Disk',
            unit='ms',
            get_value=lambda row: row.rtps.value / common.NSEC_PER_MSEC,
            get_label=lambda row: row.disk.name,
            data=result_table.rows
        )

        graph.print_graph()

    def _print_per_netif_io(self, result_table, title):
        graph = termgraph.BarGraph(
            title='Network ' + title + ' Bytes',
            label_header='Interface',
            get_value=lambda row: row.size.value,
            get_value_str=format_utils.format_size,
            get_label=lambda row: row.netif.name,
            data=result_table.rows
        )

        graph.print_graph()

    def _print_per_file_io(self, result_table, title):
        # FIXME add option to show FD owners
        # FIXME why are read and write values the same?
        graph = termgraph.BarGraph(
            title='Per-file I/O ' + title,
            label_header='Path',
            get_value=lambda row: row.size.value,
            get_value_str=format_utils.format_size,
            get_label=lambda row: row.path.path,
            data=result_table.rows
        )

        graph.print_graph()

    def _print_usage(self, usage_tables):
        self._print_per_proc_io(usage_tables.per_proc_read, 'Read')
        self._print_per_proc_io(usage_tables.per_proc_write, 'Write')
        self._print_per_file_io(usage_tables.per_file_read, 'Read')
        self._print_per_file_io(usage_tables.per_file_write, 'Write')
        self._print_per_proc_block_io(usage_tables.per_proc_block_read, 'Read')
        self._print_per_proc_block_io(
            usage_tables.per_proc_block_write, 'Write'
        )
        self._print_per_disk_sector(usage_tables.per_disk_sector)
        self._print_per_disk_request(usage_tables.per_disk_request)
        self._print_per_disk_rtps(usage_tables.per_disk_rtps)
        self._print_per_netif_io(usage_tables.per_netif_recv, 'Received')
        self._print_per_netif_io(usage_tables.per_netif_send, 'Sent')

    def _fill_freq_result_table(self, duration_list, result_table):
        if not duration_list:
            return

        # The number of bins for the histogram
        resolution = self._args.freq_resolution

        min_duration = min(duration_list)
        max_duration = max(duration_list)
        # ns to µs
        min_duration /= 1000
        max_duration /= 1000

        step = (max_duration - min_duration) / resolution

        if step == 0:
            return

        buckets = []
        values = []

        for i in range(resolution):
            buckets.append(i * step)
            values.append(0)

        for duration in duration_list:
            duration /= 1000
            index = min(int((duration - min_duration) / step), resolution - 1)
            values[index] += 1

        for index, value in enumerate(values):
            result_table.append_row(
                latency_lower=mi.Duration.from_us(index * step + min_duration),
                latency_upper=mi.Duration.from_us((index + 1) * step +
                                                  min_duration),
                count=mi.Integer(value),
            )

    def _get_disk_freq_result_tables(self, begin, end):
        result_tables = []

        for disk in self._analysis.disks.values():
            rq_durations = [rq.duration for rq in disk.rq_list if
                            self._filter_io_request(rq)]
            subtitle = 'disk: {}'.format(disk.disk_name)
            result_table = \
                self._mi_create_result_table(self._MI_TABLE_CLASS_FREQ,
                                             begin, end, subtitle)
            self._fill_freq_result_table(rq_durations, result_table)
            result_tables.append(result_table)

        return result_tables

    def _get_syscall_freq_result_tables(self, begin, end):
        open_table = \
            self._mi_create_result_table(self._MI_TABLE_CLASS_FREQ,
                                         begin, end, 'open')
        read_table = \
            self._mi_create_result_table(self._MI_TABLE_CLASS_FREQ,
                                         begin, end, 'read')
        write_table = \
            self._mi_create_result_table(self._MI_TABLE_CLASS_FREQ,
                                         begin, end, 'write')
        sync_table = \
            self._mi_create_result_table(self._MI_TABLE_CLASS_FREQ,
                                         begin, end, 'sync')
        self._fill_freq_result_table([io_rq.duration for io_rq in
                                      self._analysis.open_io_requests if
                                      self._filter_io_request(io_rq)],
                                     open_table)
        self._fill_freq_result_table([io_rq.duration for io_rq in
                                      self._analysis.read_io_requests if
                                      self._filter_io_request(io_rq)],
                                     read_table)
        self._fill_freq_result_table([io_rq.duration for io_rq in
                                      self._analysis.write_io_requests if
                                      self._filter_io_request(io_rq)],
                                     write_table)
        self._fill_freq_result_table([io_rq.duration for io_rq in
                                      self._analysis.sync_io_requests if
                                      self._filter_io_request(io_rq)],
                                     sync_table)

        return [open_table, read_table, write_table, sync_table]

    def _get_freq_result_tables(self, begin, end):
        syscall_tables = self._get_syscall_freq_result_tables(begin, end)
        disk_tables = self._get_disk_freq_result_tables(begin, end)

        return syscall_tables + disk_tables

    def _print_one_freq(self, result_table):
        graph = termgraph.FreqGraph(
            data=result_table.rows,
            get_value=lambda row: row.count.value,
            get_lower_bound=lambda row: row.latency_lower.to_us(),
            title='{} {}'.format(result_table.title, result_table.subtitle),
            unit='µs'
        )

        graph.print_graph()

    def _print_freq(self, freq_tables):
        for freq_table in freq_tables:
            self._print_one_freq(freq_table)

    def _append_log_row(self, io_rq, result_table):
        if io_rq.size is None:
            size = mi.Empty()
        else:
            size = mi.Size(io_rq.size)

        tid = io_rq.tid
        proc_stats = self._analysis.tids[tid]
        proc_name = proc_stats.comm

        # TODO: handle fd_in/fd_out for RW type operations
        if io_rq.fd is None:
            path = mi.Empty()
            fd = mi.Empty()
        else:
            fd = mi.Fd(io_rq.fd)
            parent_proc = proc_stats

            if parent_proc.pid is not None:
                parent_proc = self._analysis.tids[parent_proc.pid]

            fd_stats = parent_proc.get_fd(io_rq.fd, io_rq.end_ts)

            if fd_stats is not None:
                path = mi.Path(fd_stats.filename)
            else:
                path = mi.Unknown()

        result_table.append_row(
            time_range=mi.TimeRange(io_rq.begin_ts, io_rq.end_ts),
            out_of_range=mi.Boolean(self._is_io_rq_out_of_range(io_rq)),
            duration=mi.Duration(io_rq.duration),
            syscall=mi.Syscall(io_rq.syscall_name),
            size=size,
            process=mi.Process(proc_name, tid=tid),
            path=path,
            fd=fd,
        )

    def _fill_log_result_table(self, rq_list, sort_key, is_top, result_table):
        if not rq_list:
            return

        count = 0

        for io_rq in sorted(rq_list, key=operator.attrgetter(sort_key),
                            reverse=is_top):
            if is_top and count > self._args.limit:
                break

            self._append_log_row(io_rq, result_table)
            count += 1

    def _fill_log_result_table_from_io_requests(self, io_requests, sort_key,
                                                is_top, result_table):
        io_requests = [io_rq for io_rq in io_requests if
                       self._filter_io_request(io_rq)]
        self._fill_log_result_table(io_requests, sort_key, is_top,
                                    result_table)

    def _get_top_result_tables(self, begin, end):
        open_table = \
            self._mi_create_result_table(self._MI_TABLE_CLASS_TOP_SYSCALL,
                                         begin, end, 'open')
        read_table = \
            self._mi_create_result_table(self._MI_TABLE_CLASS_TOP_SYSCALL,
                                         begin, end, 'read')
        write_table = \
            self._mi_create_result_table(self._MI_TABLE_CLASS_TOP_SYSCALL,
                                         begin, end, 'write')
        sync_table = \
            self._mi_create_result_table(self._MI_TABLE_CLASS_TOP_SYSCALL,
                                         begin, end, 'sync')
        self._fill_log_result_table_from_io_requests(
            self._analysis.open_io_requests, 'duration', True, open_table)
        self._fill_log_result_table_from_io_requests(
            self._analysis.read_io_requests, 'duration', True, read_table)
        self._fill_log_result_table_from_io_requests(
            self._analysis.write_io_requests, 'duration', True, write_table)
        self._fill_log_result_table_from_io_requests(
            self._analysis.sync_io_requests, 'duration', True, sync_table)

        return [open_table, read_table, write_table, sync_table]

    def _print_log_row(self, row):
        fmt = '{:<40} {:<16} {:>16} {:>11}  {:<24} {:<8} {:<14}'
        begin_time = common.ns_to_hour_nsec(row.time_range.begin,
                                            self._args.multi_day,
                                            self._args.gmt)
        end_time = common.ns_to_hour_nsec(row.time_range.end,
                                          self._args.multi_day,
                                          self._args.gmt)
        time_range_str = '[' + begin_time + ',' + end_time + ']'
        duration_str = '%0.03f' % row.duration.to_us()

        if type(row.size) is mi.Empty:
            size = 'N/A'
        else:
            size = format_utils.format_size(row.size.value)

        tid = row.process.tid
        proc_name = row.process.name

        if type(row.fd) is mi.Empty:
            file_str = 'N/A'
        else:
            if type(row.path) is mi.Unknown:
                path = 'unknown'
            else:
                path = row.path.path

            file_str = '%s (fd=%s)' % (path, row.fd.fd)

        if row.out_of_range.value:
            time_range_str += '*'
            duration_str += '*'
        else:
            time_range_str += ' '
            duration_str += ' '

        print(fmt.format(time_range_str, row.syscall.name, duration_str,
                         size, proc_name, tid, file_str))

    def _print_log(self, result_table):
        if not result_table.rows:
            return

        has_out_of_range_rq = False

        print()
        fmt = '{} {} (usec)'
        print(fmt.format(result_table.title, result_table.subtitle))
        header_fmt = '{:<19} {:<20} {:<16} {:<23} {:<5} {:<24} {:<8} {:<14}'
        print(header_fmt.format(
            'Begin', 'End', 'Name', 'Duration (usec)', 'Size', 'Proc', 'PID',
            'Filename'))

        for row in result_table.rows:
            self._print_log_row(row)

            if not has_out_of_range_rq and row.out_of_range.value:
                has_out_of_range_rq = True

        if has_out_of_range_rq:
            print('*: Syscalls started and/or completed outside of the '
                  'range specified')

    def _print_top(self, top_tables):
        for table in top_tables:
            self._print_log(table)

    def _get_log_result_table(self, begin, end):
        log_table = self._mi_create_result_table(self._MI_TABLE_CLASS_LOG,
                                                 begin, end)
        self._fill_log_result_table_from_io_requests(
            self._analysis.io_requests, 'begin_ts', False, log_table)

        return log_table

    def _append_latency_stats_row(self, obj, rq_durations, result_table):
        rq_count = len(rq_durations)
        total_duration = sum(rq_durations)

        if len(rq_durations) > 0:
            min_duration = min(rq_durations)
            max_duration = max(rq_durations)
        else:
            min_duration = 0
            max_duration = 0

        if rq_count < 2:
            stdev = mi.Unknown()
        else:
            stdev = mi.Duration(statistics.stdev(rq_durations))

        if rq_count > 0:
            avg = total_duration / rq_count
        else:
            avg = 0

        result_table.append_row(
            obj=obj,
            count=mi.Integer(rq_count),
            min_latency=mi.Duration(min_duration),
            avg_latency=mi.Duration(avg),
            max_latency=mi.Duration(max_duration),
            stdev_latency=stdev,
        )

    def _append_latency_stats_row_from_requests(self, obj, io_requests,
                                                result_table):
        rq_durations = [io_rq.duration for io_rq in io_requests if
                        self._filter_io_request(io_rq)]
        self._append_latency_stats_row(obj, rq_durations, result_table)

    def _get_syscall_latency_stats_result_table(self, begin, end):
        result_table = self._mi_create_result_table(
            self._MI_TABLE_CLASS_SYSCALL_LATENCY_STATS, begin, end)
        append_fn = self._append_latency_stats_row_from_requests
        append_fn(mi.String('Open'), self._analysis.open_io_requests,
                  result_table)
        append_fn(mi.String('Read'), self._analysis.read_io_requests,
                  result_table)
        append_fn(mi.String('Write'), self._analysis.write_io_requests,
                  result_table)
        append_fn(mi.String('Sync'), self._analysis.sync_io_requests,
                  result_table)

        return result_table

    def _get_disk_latency_stats_result_table(self, begin, end):
        if not self._analysis.disks:
            return

        result_table = self._mi_create_result_table(
            self._MI_TABLE_CLASS_PART_LATENCY_STATS, begin, end)

        for disk in self._analysis.disks.values():
            if disk.rq_count:
                rq_durations = [rq.duration for rq in disk.rq_list if
                                self._filter_io_request(rq)]
                disk = mi.Disk(disk.disk_name)
                self._append_latency_stats_row(disk, rq_durations,
                                               result_table)

        return result_table

    def _get_latency_stats_result_tables(self, begin, end):
        syscall_tbl = self._get_syscall_latency_stats_result_table(begin, end)
        disk_tbl = self._get_disk_latency_stats_result_table(begin, end)

        return syscall_tbl, disk_tbl

    def _print_latency_stats_row(self, row):
        if type(row.stdev_latency) is mi.Unknown:
            stdev = '?'
        else:
            stdev = '%0.03f' % row.stdev_latency.to_us()

        avg = '%0.03f' % row.avg_latency.to_us()
        min_duration = '%0.03f' % row.min_latency.to_us()
        max_duration = '%0.03f' % row.max_latency.to_us()

        print(IoAnalysisCommand._LATENCY_STATS_FORMAT.format(
            str(row.obj), row.count.value, min_duration,
            avg, max_duration, stdev))

    def _print_syscall_latency_stats(self, stats_table):
        print('\nSyscalls latency statistics (usec):')
        print(IoAnalysisCommand._LATENCY_STATS_FORMAT.format(
            'Type', 'Count', 'Min', 'Average', 'Max', 'Stdev'))
        print(IoAnalysisCommand._SECTION_SEPARATOR_STRING)

        for row in stats_table.rows:
            self._print_latency_stats_row(row)

    def _print_disk_latency_stats(self, stats_table):
        if not stats_table.rows:
            return

        print('\nDisk latency statistics (usec):')
        print(IoAnalysisCommand._LATENCY_STATS_FORMAT.format(
            'Name', 'Count', 'Min', 'Average', 'Max', 'Stdev'))
        print(IoAnalysisCommand._SECTION_SEPARATOR_STRING)

        for row in stats_table.rows:
            self._print_latency_stats_row(row)

    def _print_latency_stats(self, syscall_latency_stats_table,
                             disk_latency_stats_table):
        self._print_syscall_latency_stats(syscall_latency_stats_table)
        self._print_disk_latency_stats(disk_latency_stats_table)

    def _add_arguments(self, ap):
        Command._add_proc_filter_args(ap)
        Command._add_min_max_args(ap)
        Command._add_log_args(
            ap, help='Output the I/O requests in chronological order')
        Command._add_top_args(
            ap, help='Output the top I/O latencies by category')
        Command._add_stats_args(ap, help='Output the I/O latency statistics')
        Command._add_freq_args(
            ap, help='Output the I/O latency frequency distribution')
        ap.add_argument('--usage', action='store_true',
                        help='Output the I/O usage')
        ap.add_argument('--minsize', type=float,
                        help='Filter out, I/O operations working with '
                        'less that minsize bytes')
        ap.add_argument('--maxsize', type=float,
                        help='Filter out, I/O operations working with '
                        'more that maxsize bytes')


def _run(mi_mode):
    iocmd = IoAnalysisCommand(mi_mode=mi_mode)
    iocmd.run()


def _runstats(mi_mode):
    sys.argv.insert(1, '--stats')
    _run(mi_mode)


def _runlog(mi_mode):
    sys.argv.insert(1, '--log')
    _run(mi_mode)


def _runfreq(mi_mode):
    sys.argv.insert(1, '--freq')
    _run(mi_mode)


def _runlatencytop(mi_mode):
    sys.argv.insert(1, '--top')
    _run(mi_mode)


def _runusage(mi_mode):
    sys.argv.insert(1, '--usage')
    _run(mi_mode)


def runstats():
    _runstats(mi_mode=False)


def runlog():
    _runlog(mi_mode=False)


def runfreq():
    _runfreq(mi_mode=False)


def runlatencytop():
    _runlatencytop(mi_mode=False)


def runusage():
    _runusage(mi_mode=False)


def runstats_mi():
    _runstats(mi_mode=True)


def runlog_mi():
    _runlog(mi_mode=True)


def runfreq_mi():
    _runfreq(mi_mode=True)


def runlatencytop_mi():
    _runlatencytop(mi_mode=True)


def runusage_mi():
    _runusage(mi_mode=True)
