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
from linuxautomaton import sv


class IoAnalysis(Analysis):
    def __init__(self, state):
        notification_cbs = {
            'net_dev_xmit': self._process_net_dev_xmit,
            'netif_receive_skb': self._process_netif_receive_skb,
            'block_rq_complete': self._process_block_rq_complete
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

        self.tids[proc.tid].update_stats(req)

    def _process_lttng_statedump_block_device(self, event):
        dev = event['dev']
        disk_name = event['diskname']

        if dev not in self.disks:
            self.disks[dev] = DiskStats(dev, disk_name)
        else:
            self.disks[dev].disk_name = disk_name


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

    def update_stats(self, req):
        if isinstance(req, sv.BlockIORequest):
            self._update_block_stats(req)
        else:
            self._update_io_stats(req)

        self.rq_list.append(req)

    def _update_block_stats(self, req):
        if req.operation is sv.IORequest.OP_READ:
            self.block_read += req.size
        elif req.operation is sv.IORequest.OP_WRITE:
            self.block_write += req.size

    def _update_io_stats(self, req):
        pass

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
