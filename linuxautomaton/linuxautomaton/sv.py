#!/usr/bin/env python3
#
# The MIT License (MIT)
#
# Copyright (C) 2015 - Julien Desfossez <jdesfosez@efficios.com>
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
    def __init__(self):
        self.tid = -1
        self.pid = -1
        self.comm = ""
        # indexed by fd
        self.fds = {}
        # indexed by filename
        self.closed_fds = {}
        # filenames (indexed by timestamp) associated with given fd (top-level
        # index) at a given point in time
        self.chrono_fds = {}
        self.current_syscall = {}
        self.init_counts()

    def init_counts(self):
        self.cpu_ns = 0
        self.migrate_count = 0
        # network read/write
        self.net_read = 0
        self.net_write = 0
        # disk read/write (might be cached)
        self.disk_read = 0
        self.disk_write = 0
        # actual block access read/write
        self.block_read = 0
        self.block_write = 0
        # unclassified read/write (FD passing and statedump)
        self.unk_read = 0
        self.unk_write = 0
        # total I/O read/write
        self.read = 0
        self.write = 0
        # last TS where the process was scheduled in
        self.last_sched = None
        # the process scheduled before this one
        self.prev_tid = -1
        # indexed by syscall_name
        self.syscalls = {}
        self.perf = {}
        self.dirty = 0
        self.allocated_pages = 0
        self.freed_pages = 0
        self.total_syscalls = 0
        # array of IORequest objects for freq analysis later (block and
        # syscalls with no FD like sys_sync)
        self.iorequests = []

    def track_chrono_fd(self, fd, filename, fdtype, timestamp):
        chrono_metadata = {}
        chrono_metadata["filename"] = filename
        chrono_metadata["fdtype"] = fdtype

        if fd not in self.chrono_fds:
            self.chrono_fds[fd] = OrderedDict()
            self.chrono_fds[fd][timestamp] = chrono_metadata
        else:
            chrono_fd = self.chrono_fds[fd]
            last_ts = next(reversed(chrono_fd))
            if filename != chrono_fd[last_ts]["filename"]:
                chrono_fd[timestamp] = chrono_metadata


class CPU():
    def __init__(self):
        self.cpu_id = -1
        self.cpu_ns = 0
        self.current_tid = -1
        self.start_task_ns = 0
        self.perf = {}
        self.wakeup_queue = []


class Syscall():
    # One instance for each unique syscall name per process
    def __init__(self):
        self.name = ""
        self.count = 0
        # duration min/max
        self.min = None
        self.max = 0
        self.total_duration = 0
        # list of all syscall events (SyscallEvent)
        self.rq = []


class SyscallEvent():
    def __init__(self):
        self.entry_ts = None
        self.exit_ts = None
        self.ret = None
        self.duration = None


class Disk():
    def __init__(self):
        self.name = ""
        self.prettyname = ""
        self.init_counts()

    def init_counts(self):
        self.nr_sector = 0
        self.nr_requests = 0
        self.completed_requests = 0
        self.request_time = 0
        self.pending_requests = {}
        self.rq_list = []
        self.max = None
        self.min = None
        self.total = None
        self.count = None
        self.rq_values = None
        self.stdev = None


class Iface():
    def __init__(self):
        self.name = ""
        self.init_counts()

    def init_counts(self):
        self.recv_bytes = 0
        self.recv_packets = 0
        self.send_bytes = 0
        self.send_packets = 0


class FDType():
    unknown = 0
    disk = 1
    net = 2
    # not 100% sure they are network FDs (assumed when net_dev_xmit is
    # called during a write syscall and the type in unknown).
    maybe_net = 3


class FD():
    def __init__(self):
        self.filename = ""
        self.fd = -1
        # address family
        self.family = socket.AF_UNSPEC
        self.fdtype = FDType.unknown
        # if FD was inherited, parent PID
        self.parent = -1
        self.init_counts()

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
        self.open = 0
        self.close = 0
        self.cloexec = 0
        # array of syscall IORequest objects for freq analysis later
        self.iorequests = []


class IRQ():
    HARD_IRQ = 1
    SOFT_IRQ = 2
    # from include/linux/interrupt.h
    soft_names = {0: "HI_SOFTIRQ",
                  1: "TIMER_SOFTIRQ",
                  2: "NET_TX_SOFTIRQ",
                  3: "NET_RX_SOFTIRQ",
                  4: "BLOCK_SOFTIRQ",
                  5: "BLOCK_IOPOLL_SOFTIRQ",
                  6: "TASKLET_SOFTIRQ",
                  7: "SCHED_SOFTIRQ",
                  8: "HRTIMER_SOFTIRQ",
                  9: "RCU_SOFTIRQ"}

    def __init__(self):
        self.nr = -1
        self.irqclass = 0
        self.start_ts = -1
        self.stop_ts = -1
        self.raise_ts = -1
        self.cpu_id = -1

    # used to track statistics about individual IRQs
    def init_irq_instance():
        irq = {}
        irq["list"] = []
        irq["max"] = 0
        irq["min"] = -1
        irq["count"] = 0
        irq["total"] = 0
        irq["raise_max"] = 0
        irq["raise_min"] = -1
        irq["raise_count"] = 0
        irq["raise_total"] = 0
        return irq


class IORequest():
    # I/O "type"
    IO_SYSCALL = 1
    IO_BLOCK = 2
    IO_NET = 3
    # I/O operations
    OP_OPEN = 1
    OP_READ = 2
    OP_WRITE = 3
    OP_CLOSE = 4
    OP_SYNC = 5

    def __init__(self):
        # IORequest.IO_*
        self.iotype = None
        # bytes for syscalls and net, sectors for block
        # FIXME: syscalls handling vectors (vector size missing)
        self.size = None
        # for syscalls and block: delay between issue and completion
        # of the request
        self.duration = None
        # IORequest.OP_*
        self.operation = None
        # syscall name
        self.name = None
        # begin syscall timestamp
        self.begin = None
        # end syscall timestamp
        self.end = None
        # current process
        self.proc = None
        # current FD (for syscalls)
        self.fd = None
        # buffers dirtied during the operation
        self.dirty = 0
        # pages allocated during the operation
        self.page_alloc = 0
        # pages freed during the operation
        self.page_free = 0
        # pages written on disk during the operation
        self.page_written = 0
        # kswapd was forced to wakeup during the operation
        self.woke_kswapd = False
        # estimated pages flushed during a sync operation
        self.page_cleared = 0


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
    DISK_OPEN_SYSCALLS = ["sys_open", "syscall_entry_open",
                          "sys_openat", "syscall_entry_openat"]
    # list of syscalls that open a FD on the network
    # (in the exit_syscall event)
    NET_OPEN_SYSCALLS = ["sys_accept", "syscall_entry_accept",
                         "sys_socket", "syscall_entry_socket"]
    # list of syscalls that can duplicate a FD
    DUP_OPEN_SYSCALLS = ["sys_fcntl", "syscall_entry_fcntl",
                         "sys_dup2", "syscall_entry_dup2"]
    SYNC_SYSCALLS = ["sys_sync", "syscall_entry_sync",
                     "sys_sync_file_range", "syscall_entry_sync_file_range",
                     "sys_fsync", "syscall_entry_fsync",
                     "sys_fdatasync", "syscall_entry_fdatasync"]
    # merge the 3 open lists
    OPEN_SYSCALLS = DISK_OPEN_SYSCALLS + NET_OPEN_SYSCALLS + DUP_OPEN_SYSCALLS
    # list of syscalls that close a FD (in the "fd =" field)
    CLOSE_SYSCALLS = ["sys_close", "syscall_entry_close"]
    # list of syscall that read on a FD, value in the exit_syscall following
    READ_SYSCALLS = ["sys_read", "syscall_entry_read",
                     "sys_recvmsg", "syscall_entry_recvmsg",
                     "sys_recvfrom", "syscall_entry_recvfrom",
                     "sys_splice", "syscall_entry_splice",
                     "sys_readv", "syscall_entry_readv",
                     "sys_sendfile64", "syscall_entry_sendfile64"]
    # list of syscall that write on a FD, value in the exit_syscall following
    WRITE_SYSCALLS = ["sys_write", "syscall_entry_write",
                      "sys_sendmsg", "syscall_entry_sendmsg",
                      "sys_sendto", "syscall_entry_sendto",
                      "sys_writev", "syscall_entry_writev"]
    # All I/O related syscalls
    IO_SYSCALLS = OPEN_SYSCALLS + CLOSE_SYSCALLS + READ_SYSCALLS + \
        WRITE_SYSCALLS
    # generic names assigned to special FDs, don't try to match these in the
    # closed_fds dict
    GENERIC_NAMES = ["unknown", "socket"]

    def __init__():
        pass
