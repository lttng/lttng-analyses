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
from . import sp, sv, common
from babeltrace import CTFScope


class IoStateProvider(sp.StateProvider):
    def __init__(self, state):
        cbs = {
            'syscall_entry': self._process_syscall_entry,
            'syscall_exit': self._process_syscall_exit,
            'syscall_entry_connect': self._process_connect,
            'writeback_pages_written': self._process_writeback_pages_written,
            'mm_vmscan_wakeup_kswapd': self._process_mm_vmscan_wakeup_kswapd,
            'mm_page_free': self._process_mm_page_free
        }

        self._state = state
        self._register_cbs(cbs)

    def process_event(self, ev):
        self._process_event_cb(ev)

    def _process_syscall_entry(self, event):
        # Only handle IO Syscalls
        name = common.get_syscall_name(event)
        if name not in sv.SyscallConsts.IO_SYSCALLS:
            return

        cpu_id = event['cpu_id']
        if cpu_id not in self._state.cpus:
            return

        cpu = self._state.cpus[cpu_id]
        if cpu.current_tid is None:
            return

        proc = self._state.tids[cpu.current_tid]

        # check if we can fix the pid from a context
        self._fix_context_pid(event, proc)

        if name in sv.SyscallConsts.OPEN_SYSCALLS:
            self._track_open(event, name, proc)
        elif name in sv.SyscallConsts.CLOSE_SYSCALLS:
            self._track_close(event, name, proc)
        elif name in sv.SyscallConsts.READ_SYSCALLS or \
                name in sv.SyscallConsts.WRITE_SYSCALLS:
            self._track_read_write(event, name, proc)
        elif name in sv.SyscallConsts.SYNC_SYSCALLS:
            self._track_sync(event, name, proc)

    def _process_syscall_exit(self, event):
        cpu_id = event['cpu_id']
        if cpu_id not in self._state.cpus:
            return

        cpu = self._state.cpus[cpu_id]
        if cpu.current_tid is None:
            return

        proc = self._state.tids[cpu.current_tid]
        current_syscall = proc.current_syscall
        if current_syscall is None:
            return

        name = current_syscall.name
        if name not in sv.SyscallConsts.IO_SYSCALLS:
            return

        self._track_io_rq_exit(event, proc)

        proc.current_syscall = None

    def _process_connect(self, event):
        cpu_id = event['cpu_id']
        if cpu_id not in self._state.cpus:
            return

        cpu = self._state.cpus[cpu_id]
        if cpu.current_tid is None:
            return

        proc = self._state.tids[cpu.current_tid]
        parent_proc = self._get_parent_proc(proc)

        # FIXME: handle on syscall_exit_connect only when succesful
        if 'family' in event and event['family'] == socket.AF_INET:
            fd = event['fd']
            if fd in parent_proc.fds:
                parent_proc.fds[fd].filename = (
                    '%s:%d' % (common.get_v4_addr_str(event['v4addr']),
                               event['dport']))

    def _process_writeback_pages_written(self, event):
        for cpu in self._state.cpus.values():
            if cpu.current_tid is None:
                continue

            current_syscall = self._state.tids[cpu.current_tid].current_syscall
            if current_syscall is None:
                continue

            if current_syscall.io_rq:
                current_syscall.io_rq.pages_written += event['pages']

    def _process_mm_vmscan_wakeup_kswapd(self, event):
        cpu_id = event['cpu_id']
        if cpu_id not in self._state.cpus:
            return

        cpu = self._state.cpus[cpu_id]
        if cpu.current_tid is None:
            return

        current_syscall = self._state.tids[cpu.current_tid].current_syscall
        if current_syscall is None:
            return

        if current_syscall.io_rq:
            current_syscall.io_rq.woke_kswapd = True

    def _process_mm_page_free(self, event):
        for cpu in self._state.cpus.values():
            if cpu.current_tid is None:
                continue

            proc = self._state.tids[cpu.current_tid]

            # if the current process is kswapd0, we need to
            # attribute the page freed to the process that
            # woke it up.
            if proc.comm == 'kswapd0' and proc.prev_tid > 0:
                proc = self._state.tids[proc.prev_tid]

            current_syscall = proc.current_syscall
            if current_syscall is None:
                continue

            if current_syscall.io_rq and current_syscall.io_rq.woke_kswapd:
                current_syscall.io_rq.pages_freed += 1

    def _track_open(self, event, name, proc):
        current_syscall = proc.current_syscall
        if name in sv.SyscallConsts.DISK_OPEN_SYSCALLS:
            current_syscall.io_rq = sv.OpenIORequest.new_from_disk_open(
                event, proc.tid)
        elif name in ['accept', 'accept4']:
            current_syscall.io_rq = sv.OpenIORequest.new_from_accept(
                event, proc.tid)
        elif name == 'socket':
            current_syscall.io_rq = sv.OpenIORequest.new_from_socket(
                event, proc.tid)
        elif name in sv.SyscallConsts.DUP_OPEN_SYSCALLS:
            self._track_dup(event, name, proc)

    def _track_dup(self, event, name, proc):
        current_syscall = proc.current_syscall

        # If the process that triggered the io_rq is a thread,
        # its FDs are that of the parent process
        parent_proc = self._get_parent_proc(proc)
        fds = parent_proc.fds

        if name == 'dup':
            oldfd = event['fildes']
        elif name in ['dup2', 'dup3']:
            oldfd = event['oldfd']
            newfd = event['newfd']
            if newfd in fds:
                self._close_fd(parent_proc, newfd, event.timestamp)
        elif name == 'fcntl':
            # Only handle if cmd == F_DUPFD (0)
            if event['cmd'] != 0:
                return

            oldfd = event['fd']

        old_file = None
        if oldfd in fds:
            old_file = fds[oldfd]

        current_syscall.io_rq = sv.OpenIORequest.new_from_old_fd(
            event, proc.tid, old_file)

        if name == 'dup3':
            cloexec = event['flags'] & common.O_CLOEXEC == common.O_CLOEXEC
            current_syscall.io_rq.cloexec = cloexec

    def _track_close(self, event, name, proc):
        proc.current_syscall.io_rq = sv.CloseIORequest(
            event.timestamp, proc.tid, event['fd'])

    def _track_read_write(self, event, name, proc):
        current_syscall = proc.current_syscall

        if name == 'splice':
            current_syscall.io_rq = sv.ReadWriteIORequest.new_from_splice(
                event, proc.tid)
            return
        elif name == 'sendfile64':
            current_syscall.io_rq = sv.ReadWriteIORequest.new_from_sendfile64(
                event, proc.tid)
            return

        if name in ['writev', 'pwritev', 'readv', 'preadv']:
            size_key = 'vlen'
        elif name == 'recvfrom':
            size_key = 'size'
        elif name == 'sendto':
            size_key = 'len'
        elif name in ['recvmsg', 'sendmsg']:
            size_key = None
        else:
            size_key = 'count'

        current_syscall.io_rq = sv.ReadWriteIORequest.new_from_fd_event(
            event, proc.tid, size_key)

    def _track_sync(self, event, name, proc):
        current_syscall = proc.current_syscall

        if name == 'sync':
            current_syscall.io_rq = sv.SyncIORequest.new_from_sync(
                event, proc.tid)
        elif name in ['fsync', 'fdatasync']:
            current_syscall.io_rq = sv.SyncIORequest.new_from_fsync(
                event, proc.tid)
        elif name == 'sync_file_range':
            current_syscall.io_rq = sv.SyncIORequest.new_from_sync_file_range(
                event, proc.tid)

    def _track_io_rq_exit(self, event, proc):
        ret = event['ret']
        io_rq = proc.current_syscall.io_rq
        # io_rq can be None in the case of fcntl when cmd is not
        # F_DUPFD, in which case we disregard the syscall as it did
        # not open any FD
        if io_rq is None:
            return

        io_rq.update_from_exit(event)

        if ret >= 0:
            self._create_fd(proc, io_rq)

        parent_proc = self._get_parent_proc(proc)
        self._state.send_notification_cb('io_rq_exit',
                                         io_rq=io_rq,
                                         proc=proc,
                                         parent_proc=parent_proc)

        if isinstance(io_rq, sv.CloseIORequest) and ret == 0:
            self._close_fd(proc, io_rq.fd, io_rq.end_ts)

    def _create_fd(self, proc, io_rq):
        parent_proc = self._get_parent_proc(proc)

        if io_rq.fd is not None and io_rq.fd not in parent_proc.fds:
            if isinstance(io_rq, sv.OpenIORequest):
                parent_proc.fds[io_rq.fd] = sv.FD.new_from_open_rq(io_rq)
            else:
                parent_proc.fds[io_rq.fd] = sv.FD(io_rq.fd)

            self._state.send_notification_cb('create_fd',
                                             fd=io_rq.fd,
                                             parent_proc=parent_proc,
                                             timestamp=io_rq.end_ts)
        elif isinstance(io_rq, sv.ReadWriteIORequest):
            if io_rq.fd_in is not None and io_rq.fd_in not in parent_proc.fds:
                parent_proc.fds[io_rq.fd_in] = sv.FD(io_rq.fd_in)
                self._state.send_notification_cb('create_fd',
                                                 fd=io_rq.fd_in,
                                                 parent_proc=parent_proc,
                                                 timestamp=io_rq.end_ts)

            if io_rq.fd_out is not None and \
               io_rq.fd_out not in parent_proc.fds:
                parent_proc.fds[io_rq.fd_out] = sv.FD(io_rq.fd_out)
                self._state.send_notification_cb('create_fd',
                                                 fd=io_rq.fd_out,
                                                 parent_proc=parent_proc,
                                                 timestamp=io_rq.end_ts)

    def _close_fd(self, proc, fd, timestamp):
        parent_proc = self._get_parent_proc(proc)
        self._state.send_notification_cb('close_fd',
                                         fd=fd,
                                         parent_proc=parent_proc,
                                         timestamp=timestamp)
        del parent_proc.fds[fd]

    def _get_parent_proc(self, proc):
        if proc.pid is not None and proc.tid != proc.pid:
            parent_proc = self._state.tids[proc.pid]
        else:
            parent_proc = proc

        return parent_proc

    def _fix_context_pid(self, event, proc):
        for context in event.field_list_with_scope(
                CTFScope.STREAM_EVENT_CONTEXT):
            if context != 'pid':
                continue
            # make sure the 'pid' field is not also in the event
            # payload, otherwise we might clash
            for context in event.field_list_with_scope(
                    CTFScope.EVENT_FIELDS):
                if context == 'pid':
                    return

            if proc.pid is None:
                proc.pid = event['pid']
                if event['pid'] != proc.tid:
                    proc.pid = event['pid']
                    parent_proc = sv.Process(proc.pid, proc.pid, proc.comm)
                    self._state.tids[parent_proc.pid] = parent_proc
