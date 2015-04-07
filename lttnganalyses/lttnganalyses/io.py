#!/usr/bin/env python3
#
# The MIT License (MIT)
#
# Copyright (C) 2015 - Antoine Busque <abusque@efficios.com>
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

from .analysis import Analysis
from linuxautomaton import sv, statedump


class IoAnalysis(Analysis):
    def __init__(self, state):
        notification_cbs = {
            'net_dev_xmit': self._process_net_dev_xmit,
            'netif_receive_skb': self._process_netif_receive_skb,
            'block_rq_complete': self._process_block_rq_complete,
            'io_rq_exit': self._process_io_rq_exit,
            'create_fd': self._process_create_fd,
            'close_fd': self._process_close_fd,
            'create_parent_proc': self._process_create_parent_proc
        }

        event_cbs = {
            'lttng_statedump_block_device':
            self._process_lttng_statedump_block_device
        }

        self._state = state
        self._state.register_notification_cbs(notification_cbs)
        self._register_cbs(event_cbs)

        self.disks = {}
        self.ifaces = {}
        self.tids = {}

    def process_event(self, ev):
        self._process_event_cb(ev)

    def reset(self):
        for dev in self.disks:
            self.disks[dev].reset()

        for name in self.ifaces:
            self.ifaces[name].reset()

        for tid in self.tids:
            self.tids[tid].reset()

    def _process_net_dev_xmit(self, **kwargs):
        name = kwargs['iface_name']
        sent_bytes = kwargs['sent_bytes']

        if name not in self.ifaces:
            self.ifaces[name] = IfaceStats(name)

        self.ifaces[name].sent_packets += 1
        self.ifaces[name].sent_bytes += sent_bytes

    def _process_netif_receive_skb(self, **kwargs):
        name = kwargs['iface_name']
        recv_bytes = kwargs['recv_bytes']

        if name not in self.ifaces:
            self.ifaces[name] = IfaceStats(name)

        self.ifaces[name].recv_packets += 1
        self.ifaces[name].recv_bytes += recv_bytes

    def _process_block_rq_complete(self, **kwargs):
        req = kwargs['req']
        proc = kwargs['proc']

        if req.dev not in self.disks:
            self.disks[req.dev] = DiskStats(req.dev)

        self.disks[req.dev].update_stats(req)

        if proc.tid not in self.tids:
            self.tids[proc.tid] = ProcessIOStats.new_from_process(proc)

        self.tids[proc.tid].update_block_stats(req)

    def _process_lttng_statedump_block_device(self, event):
        dev = event['dev']
        disk_name = event['diskname']

        if dev not in self.disks:
            self.disks[dev] = DiskStats(dev, disk_name)
        else:
            self.disks[dev].disk_name = disk_name

    def _process_io_rq_exit(self, **kwargs):
        proc = kwargs['proc']
        parent_proc = kwargs['parent_proc']
        io_rq = kwargs['io_rq']

        if proc.tid not in self.tids:
            self.tids[proc.tid] = ProcessIOStats.new_from_process(proc)

        if parent_proc.tid not in self.tids:
            self.tids[parent_proc.tid] = (
                ProcessIOStats.new_from_process(parent_proc))

        proc_stats = self.tids[proc.tid]
        parent_stats = self.tids[parent_proc.tid]

        fd_types = {}
        if io_rq.errno is None:
            if io_rq.operation == sv.IORequest.OP_READ or \
               io_rq.operation == sv.IORequest.OP_WRITE:
                fd_types['fd'] = parent_stats.fds[io_rq.fd].fd_type
            elif io_rq.operation == sv.IORequest.OP_READ_WRITE:
                fd_types['fd_in'] = parent_stats.fds[io_rq.fd_in].fd_type
                fd_types['fd_out'] = parent_stats.fds[io_rq.fd_out].fd_type

        proc_stats.update_io_stats(io_rq, fd_types)
        parent_stats.update_fd_stats(io_rq)

    def _process_create_parent_proc(self, **kwargs):
        proc = kwargs['proc']
        parent_proc = kwargs['parent_proc']

        if proc.tid not in self.tids:
            self.tids[proc.tid] = ProcessIOStats.new_from_process(proc)

        if parent_proc.tid not in self.tids:
            self.tids[parent_proc.tid] = (
                ProcessIOStats.new_from_process(parent_proc))

        proc_stats = self.tids[proc.tid]
        parent_stats = self.tids[parent_proc.tid]

        proc_stats.pid = parent_stats.tid
        statedump.StatedumpStateProvider._assign_fds_to_parent(proc_stats,
                                                               parent_stats)

    def _process_create_fd(self, **kwargs):
        parent_proc = kwargs['parent_proc']
        tid = parent_proc.tid
        fd = kwargs['fd']

        if tid not in self.tids:
            self.tids[tid] = ProcessIOStats.new_from_process(parent_proc)

        parent_stats = self.tids[tid]
        parent_stats.fds[fd] = FDStats.new_from_fd(parent_proc.fds[fd])

    def _process_close_fd(self, **kwargs):
        parent_proc = kwargs['parent_proc']
        tid = parent_proc.tid
        fd = kwargs['fd']

        parent_stats = self.tids[tid]
        # TODO mark FD as closed


class DiskStats():
    MINORBITS = 20
    MINORMASK = ((1 << MINORBITS) - 1)

    def __init__(self, dev, disk_name=None):
        self.dev = dev
        if disk_name is not None:
            self.disk_name = disk_name
        else:
            self.disk_name = DiskStats._get_name_from_dev(dev)

        self.min_rq_duration = None
        self.max_rq_duration = None
        self.total_rq_sectors = 0
        self.total_rq_duration = 0
        self.rq_list = []

    @property
    def rq_count(self):
        return len(self.rq_list)

    def update_stats(self, req):
        if self.min_rq_duration is None or req.duration < self.min_rq_duration:
            self.min_rq_duration = req.duration
        if self.max_rq_duration is None or req.duration > self.max_rq_duration:
            self.max_rq_duration = req.duration

        self.total_rq_sectors += req.nr_sector
        self.total_rq_duration += req.duration
        self.rq_list.append(req)

    def reset(self):
        self.min_rq_duration = None
        self.max_rq_duration = None
        self.total_rq_sectors = 0
        self.total_rq_duration = 0
        self.rq_list = []

    @staticmethod
    def _get_name_from_dev(dev):
        # imported from include/linux/kdev_t.h
        major = dev >> DiskStats.MINORBITS
        minor = dev & DiskStats.MINORMASK

        return '(%d,%d)' % (major, minor)


class IfaceStats():
    def __init__(self, name):
        self.name = name
        self.recv_bytes = 0
        self.recv_packets = 0
        self.sent_bytes = 0
        self.sent_packets = 0

    def reset(self):
        self.recv_bytes = 0
        self.recv_packets = 0
        self.sent_bytes = 0
        self.sent_packets = 0


class ProcessIOStats():
    def __init__(self, pid, tid, comm):
        self.pid = pid
        self.tid = tid
        self.comm = comm
        # Number of bytes read or written by the process, by type of I/O
        self.disk_read = 0
        self.disk_write = 0
        self.net_read = 0
        self.net_write = 0
        self.unk_read = 0
        self.unk_write = 0
        # Actual number of bytes read or written by the process at the
        # block layer
        self.block_read = 0
        self.block_write = 0
        # FDStats objects, indexed by fd (fileno)
        self.fds = {}
        self.rq_list = []

    @classmethod
    def new_from_process(cls, proc):
        return cls(proc.pid, proc.tid, proc.comm)

    # Total read/write does not account for block layer I/O
    @property
    def total_read(self):
        return self.disk_read + self.net_read + self.unk_read

    @property
    def total_write(self):
        return self.disk_write + self.net_write + self.unk_write

    def update_fd_stats(self, req):
        if req.errno is not None:
            return

        if req.fd is not None:
            self.fds[req.fd].update_stats(req)
        elif isinstance(req, sv.ReadWriteIORequest):
            if req.fd_in is not None:
                self.fds[req.fd_in].update_stats(req)

            if req.fd_out is not None:
                self.fds[req.fd_out].update_stats(req)

    def update_block_stats(self, req):
        self.rq_list.append(req)

        if req.operation is sv.IORequest.OP_READ:
            self.block_read += req.size
        elif req.operation is sv.IORequest.OP_WRITE:
            self.block_write += req.size

    def update_io_stats(self, req, fd_types):
        self.rq_list.append(req)

        if req.size is None or req.errno is not None:
            return

        if req.operation is sv.IORequest.OP_READ:
            self._update_read(req.returned_size, fd_types['fd'])
        elif req.operation is sv.IORequest.OP_WRITE:
            self._update_write(req.returned_size, fd_types['fd'])
        elif req.operation is sv.IORequest.OP_READ_WRITE:
            self._update_read(req.returned_size, fd_types['fd_in'])
            self._update_write(req.returned_size, fd_types['fd_out'])

        self.rq_list.append(req)

    def _update_read(self, size, fd_type):
        if fd_type == sv.FDType.disk:
            self.disk_read += size
        elif fd_type == sv.FDType.net or fd_type == sv.FDType.maybe_net:
            self.net_read += size
        else:
            self.unk_read += size

    def _update_write(self, size, fd_type):
        if fd_type == sv.FDType.disk:
            self.disk_write += size
        elif fd_type == sv.FDType.net or fd_type == sv.FDType.maybe_net:
            self.net_write += size
        else:
            self.unk_write += size

    def reset(self):
        self.disk_read = 0
        self.disk_write = 0
        self.net_read = 0
        self.net_write = 0
        self.unk_read = 0
        self.unk_write = 0
        self.block_read = 0
        self.block_write = 0
        self.rq_list = []

        for fd in self.fds:
            self.fds[fd].reset()


class FDStats():
    def __init__(self, fd, filename, fd_type, cloexec, family):
        self.fd = fd
        self.filename = filename
        self.fd_type = fd_type
        self.cloexec = cloexec
        self.family = family

        # Number of bytes read or written
        self.read = 0
        self.write = 0
        # IO Requests that acted upon the FD
        self.rq_list = []

    @classmethod
    def new_from_fd(cls, fd):
        return cls(fd.fd, fd.filename, fd.fd_type, fd.cloexec, fd.family)

    def update_stats(self, req):
        if req.operation is sv.IORequest.OP_READ:
            self.read += req.returned_size
        elif req.operation is sv.IORequest.OP_WRITE:
            self.write += req.returned_size
        elif req.operation is sv.IORequest.OP_READ_WRITE:
            if self.fd == req.fd_in:
                self.read += req.returned_size
            elif self.fd == req.fd_out:
                self.write += req.returned_size

        self.rq_list.append(req)

    def reset(self):
        self.read = 0
        self.write = 0
        self.rq_list = []
