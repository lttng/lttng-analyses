#!/usr/bin/env python3
#
# The MIT License (MIT)
#
# Copyright (C) 2015 - Julien Desfossez <jdesfossez@efficios.com>
#               2015 - Antoine Busque <abusque@efficios.com>
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

import socket
from collections import OrderedDict


class StateVariable:
    pass


class Process():
    def __init__(self, tid=None, pid=None, comm=''):
        self.tid = tid
        self.pid = pid
        self.comm = comm
        # indexed by fd
        self.fds = {}
        # indexed by filename
        self.closed_fds = {}
        # filenames (indexed by timestamp) associated with given fd (top-level
        # index) at a given point in time
        self.chrono_fds = {}
        self.current_syscall = {}
        # the process scheduled before this one
        self.prev_tid = None

    def track_chrono_fd(self, fd, filename, fdtype, timestamp):
        chrono_metadata = {}
        chrono_metadata['filename'] = filename
        chrono_metadata['fdtype'] = fdtype

        if fd not in self.chrono_fds:
            self.chrono_fds[fd] = OrderedDict()
            self.chrono_fds[fd][timestamp] = chrono_metadata
        else:
            chrono_fd = self.chrono_fds[fd]
            last_ts = next(reversed(chrono_fd))
            if filename != chrono_fd[last_ts]['filename']:
                chrono_fd[timestamp] = chrono_metadata


class CPU():
    def __init__(self, cpu_id):
        self.cpu_id = cpu_id
        self.current_tid = None
        self.current_hard_irq = None
        # softirqs use a dict because multiple ones can be raised before
        # handling. They are indexed by vec, and each entry is a list,
        # ordered chronologically
        self.current_softirqs = {}


class MemoryManagement():
    def __init__(self):
        self.page_count = 0

class SyscallEvent():
    def __init__(self, name, begin_ts):
        self.name = name
        self.begin_ts = begin_ts
        self.end_ts = None
        self.ret = None
        self.duration = None

    def process_exit(self, event):
        self.end_ts = event.timestamp
        self.ret = event['ret']
        self.duration = self.end_ts - self.begin_ts

    @classmethod
    def new_from_entry(cls, event):
        return cls(event.name, event.timestamp)


class Disk():
    def __init__(self):
        # pending block IO Requests, indexed by sector
        self.pending_requests = {}


class FDType():
    unknown = 0
    disk = 1
    net = 2
    # not 100% sure they are network FDs (assumed when net_dev_xmit is
    # called during a write syscall and the type in unknown).
    maybe_net = 3


class FD():
    def __init__(self):
        self.filename = ''
        self.fd = None
        # address family
        self.family = socket.AF_UNSPEC
        self.fdtype = FDType.unknown
        # if FD was inherited, parent PID
        self.parent = None
        self.cloexec = False
        self.init_counts()

    @classmethod
    def new_from_fd(cls, fd):
        new_fd = cls()
        new_fd.filename = fd.filename
        new_fd.fd = fd.fd
        new_fd.family = fd.family
        new_fd.fdtype = fd.fdtype
        new_fd.parent = fd.parent
        new_fd.cloexec = fd.cloexec
        return new_fd

    def init_counts(self):
        # network read/write
        self.net_read = 0
        self.net_write = 0
        # disk read/write (might be cached)
        self.disk_read = 0
        self.disk_write = 0
        # unclassified read/write (FD passing and statedump)
        self.unk_read = 0
        self.unk_write = 0
        # total read/write
        self.read = 0
        self.write = 0
        # array of syscall IORequest objects for freq analysis later
        self.iorequests = []


class IRQ():
    def __init__(self, id, cpu_id, begin_ts=None):
        self.id = id
        self.cpu_id = cpu_id
        self.begin_ts = begin_ts
        self.end_ts = None


class HardIRQ(IRQ):
    def __init__(self, id, cpu_id, begin_ts):
        super().__init__(id, cpu_id, begin_ts)
        self.ret = None

    @classmethod
    def new_from_irq_handler_entry(cls, event):
        id = event['irq']
        cpu_id = event['cpu_id']
        begin_ts = event.timestamp
        return cls(id, cpu_id, begin_ts)


class SoftIRQ(IRQ):
    def __init__(self, id, cpu_id, raise_ts=None, begin_ts=None):
        super().__init__(id, cpu_id, begin_ts)
        self.raise_ts = raise_ts

    @classmethod
    def new_from_softirq_raise(cls, event):
        id = event['vec']
        cpu_id = event['cpu_id']
        raise_ts = event.timestamp
        return cls(id, cpu_id, raise_ts)

    @classmethod
    def new_from_softirq_entry(cls, event):
        id = event['vec']
        cpu_id = event['cpu_id']
        begin_ts = event.timestamp
        return cls(id, cpu_id, begin_ts=begin_ts)


class IORequest():
    # I/O operations
    OP_OPEN = 1
    OP_READ = 2
    OP_WRITE = 3
    OP_CLOSE = 4
    OP_SYNC = 5

    def __init__(self, begin_ts, size, tid, operation):
        self.begin_ts = begin_ts
        self.end_ts = None
        self.duration = None
        # request size in bytes
        self.size = size
        self.operation = operation
        # tid of process that triggered the rq
        self.tid = tid


class SyscallIORequest(IORequest):
    def __init__(self, begin_ts, size, tid, operation):
        super().__init__(begin_ts, size, tid)
        self.fd = None
        self.syscall_name = None
        # Number of pages alloc'd/freed/written to disk during the rq
        self.pages_allocated = 0
        self.pages_freed = 0
        self.pages_written = 0
        # Whether kswapd was forced to wakeup during the rq
        self.woke_kswapd = False


class BlockIORequest(IORequest):
    # Logical sector size in bytes, according to the kernel
    SECTOR_SIZE = 512

    def __init__(self, begin_ts, tid, operation, dev, sector, nr_sector):
        size = nr_sector * BlockIORequest.SECTOR_SIZE
        super().__init__(begin_ts, size, tid, operation)
        self.dev = dev
        self.sector = sector
        self.nr_sector = nr_sector

    def update_from_rq_complete(self, event):
        self.end_ts = event.timestamp
        self.duration = self.end_ts - self.begin_ts

    @classmethod
    def new_from_rq_issue(cls, event):
        begin_ts = event.timestamp
        dev = event['dev']
        sector = event['sector']
        nr_sector = event['nr_sector']
        tid = event['tid']
        # An even rwbs indicates read operation, odd indicates write
        if event['rwbs'] % 2 == 0:
            operation = IORequest.OP_READ
        else:
            operation = IORequest.OP_WRITE

        return cls(begin_ts, tid, operation, dev, sector, nr_sector)


class BlockRemapRequest():
    def __init__(self, dev, sector, old_dev, old_sector):
        self.dev = dev
        self.sector = sector
        self.old_dev = old_dev
        self.old_sector = old_sector


class Syscalls_stats():
    def __init__(self):
        self.read_max = 0
        self.read_min = None
        self.read_total = 0
        self.read_count = 0
        self.read_rq = []
        self.all_read = []

        self.write_max = 0
        self.write_min = None
        self.write_total = 0
        self.write_count = 0
        self.write_rq = []
        self.all_write = []

        self.open_max = 0
        self.open_min = None
        self.open_total = 0
        self.open_count = 0
        self.open_rq = []
        self.all_open = []

        self.sync_max = 0
        self.sync_min = None
        self.sync_total = 0
        self.sync_count = 0
        self.sync_rq = []
        self.all_sync = []


class SyscallConsts():
    # TODO: decouple socket/family logic from this class
    INET_FAMILIES = [socket.AF_INET, socket.AF_INET6]
    DISK_FAMILIES = [socket.AF_UNIX]
    # list nof syscalls that open a FD on disk (in the exit_syscall event)
    DISK_OPEN_SYSCALLS = ['open', 'openat']
    # list of syscalls that open a FD on the network
    # (in the exit_syscall event)
    NET_OPEN_SYSCALLS = ['accept', 'accept4', 'socket']
    # list of syscalls that can duplicate a FD
    DUP_OPEN_SYSCALLS = ['fcntl', 'dup', 'dup2', 'dup3']
    SYNC_SYSCALLS = ['sync', 'sync_file_range', 'fsync', 'fdatasync']
    # merge the 3 open lists
    OPEN_SYSCALLS = DISK_OPEN_SYSCALLS + NET_OPEN_SYSCALLS + DUP_OPEN_SYSCALLS
    # list of syscalls that close a FD (in the 'fd =' field)
    CLOSE_SYSCALLS = ['close']
    # list of syscall that read on a FD, value in the exit_syscall following
    READ_SYSCALLS = ['read', 'recvmsg', 'recvfrom', 'splice', 'readv',
                     'sendfile64']
    # list of syscall that write on a FD, value in the exit_syscall following
    WRITE_SYSCALLS = ['write', 'sendmsg', 'sendto', 'writev']
    # All I/O related syscalls
    IO_SYSCALLS = OPEN_SYSCALLS + CLOSE_SYSCALLS + READ_SYSCALLS + \
        WRITE_SYSCALLS + SYNC_SYSCALLS
