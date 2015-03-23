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
from linuxautomaton import sp, sv, common
from babeltrace import CTFScope

class IoStateProvider(sp.StateProvider):
    def __init__(self, state):
        cbs = {
            'syscall_entry': self._process_syscall_entry,
            'syscall_exit': self._process_syscall_exit,
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

        self._track_fds(event)

        if name in sv.SyscallConsts.READ_SYSCALLS or \
           name in sv.SyscallConsts.WRITE_SYSCALLS:
            self._track_read_write(event)
        elif name in sv.SyscallConsts.SYNC_SYSCALLS:
            self._track_sync(event)

    def _process_syscall_exit(self, event):
        ret = event['ret']
        cpu_id = event['cpu_id']
        if cpu_id not in self._state.cpus:
            return

        cpu = self._state.cpus[cpu_id]
        if cpu.current_tid is None:
            return

        proc = self._state.tids[cpu.current_tid]
        current_syscall = proc.current_syscall
        if not current_syscall:
            return

        if name not in sv.SyscallConsts.IO_SYSCALLS:
            return

        current_syscall['iorequest'] = sv.IORequest()
        current_syscall['iorequest'].iotype = sv.IORequest.IO_SYSCALL
        current_syscall['iorequest'].name = name
        if name in sv.SyscallConsts.OPEN_SYSCALLS:
            self._add_tid_fd(event)
            if ret < 0:
                return

            current_syscall['fd'] = self._get_fd(proc, ret, event)
            current_syscall['count'] = 0
            current_syscall['fd'].fdtype = current_syscall['fdtype']
            current_syscall['iorequest'].operation = sv.IORequest.OP_OPEN
            self._track_rw_latency(event)
        elif name in sv.SyscallConsts.READ_SYSCALLS or \
                name in sv.SyscallConsts.WRITE_SYSCALLS:
            self._track_read_write_return(name, ret, cpu)
            self._track_rw_latency(event)
        elif name in sv.SyscallConsts.SYNC_SYSCALLS:
            current_syscall['iorequest'].operation = sv.IORequest.OP_SYNC
            self._track_rw_latency(event)
            if name in ['sys_sync', 'syscall_entry_sync']:
                t = self._state.tids[cpu.current_tid]
                t.iorequests.append(current_syscall['iorequest'])

        if proc in self._state.pending_syscalls:
            self._state.pending_syscalls.remove(proc)

    def _process_writeback_pages_written(self, event):
        for cpu in self._state.cpus.values():
            if cpu.current_tid is None:
                continue

            current_syscall = self._state.tids[cpu.current_tid].current_syscall
            if not current_syscall:
                continue

            current_syscall['pages_written'] = event['pages']

    def _process_mm_vmscan_wakeup_kswapd(self, event):
        cpu_id = event['cpu_id']
        if cpu_id not in self._state.cpus:
            return

        cpu = self._state.cpus[cpu_id]
        if cpu.current_tid is None:
            return

        current_syscall = self._state.tids[cpu.current_tid].current_syscall
        if not current_syscall:
            return

        current_syscall['wakeup_kswapd'] = True

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
            if not current_syscall:
                continue

            if 'wakeup_kswapd' in current_syscall:
                if 'page_free' in current_syscall:
                    current_syscall['page_free'] += 1
                else:
                    current_syscall['page_free'] = 1

    def _track_fds(self, event):
        name = common.get_syscall_name(event)
        cpu_id = event['cpu_id']
        if cpu_id not in self._state.cpus:
            return

        cpu = self._state.cpus[cpu_id]
        if cpu.current_tid is None:
            return

        proc = self._state.tids[cpu.current_tid]
        # check if we can fix the pid from a context
        self._fix_context_pid(event, proc)
        # if it's a thread, we want the parent
        if proc.pid is not None and proc.tid != proc.pid:
            proc = self._state.tids[proc.pid]

        if name in sv.SyscallConsts.OPEN_SYSCALLS:
            self.track_open(name, proc, event, cpu)
        elif name in sv.SyscallConsts.CLOSE_SYSCALLS:
            self._track_close(name, proc, event, cpu)
        # when a connect occurs, no new sv.FD is returned, but we can fix
        # the 'filename' if we have the destination info
        elif name == 'connect' and event['family'] == socket.AF_INET:
            fd = self._get_fd(proc, event['fd'], event)
            ipport = '%s:%d' % (common.get_v4_addr_str(event['v4addr']),
                                event['dport'])
            fd.filename = ipport

    def _track_read_write(self, event):
        name = common.get_syscall_name(event)
        cpu_id = event['cpu_id']

        if cpu_id not in self._state.cpus:
            return

        cpu = self._state.cpus[cpu_id]
        if cpu.current_tid is None:
            return

        proc = self._state.tids[cpu.current_tid]
        self._state.pending_syscalls.append(proc)
        # if it's a thread, we want the parent
        if proc.pid is not None and proc.tid != proc.pid:
            proc = self._state.tids[proc.pid]

        current_syscall = proc.current_syscall
        current_syscall['name'] = name
        current_syscall['start'] = event.timestamp

        if name == 'splice':
            current_syscall['fd_in'] = self._get_fd(proc, event['fd_in'],
                                                    event)
            current_syscall['fd_out'] = self._get_fd(proc, event['fd_out'],
                                                     event)
            current_syscall['count'] = event['len']
            current_syscall['filename'] = current_syscall['fd_in'].filename
            return
        elif name == 'sendfile64':
            current_syscall['fd_in'] = self._get_fd(proc, event['in_fd'],
                                                    event)
            current_syscall['fd_out'] = self._get_fd(proc, event['out_fd'],
                                                     event)
            current_syscall['count'] = event['count']
            current_syscall['filename'] = current_syscall['fd_in'].filename
            return

        fileno = event['fd']
        fd = self._get_fd(proc, fileno, event)
        current_syscall['fd'] = fd
        if name in ['writev', 'readv']:
            current_syscall['count'] = event['vlen']
        elif name == 'recvfrom':
            current_syscall['count'] = event['size']
        elif name in ['recvmsg', 'sendmsg']:
            current_syscall['count'] = ''
        elif name == 'sendto':
            current_syscall['count'] = event['len']
        else:
            current_syscall['count'] = event['count']

        current_syscall['filename'] = fd.filename

    def track_open(self, name, proc, event, cpu):
        self._state.tids[cpu.current_tid].current_syscall = {}
        current_syscall = self._state.tids[cpu.current_tid].current_syscall
        if name in sv.SyscallConsts.DISK_OPEN_SYSCALLS:
            current_syscall['filename'] = event['filename']
            if event['flags'] & common.O_CLOEXEC == common.O_CLOEXEC:
                current_syscall['cloexec'] = True
        elif name in ['accept', 'accept4']:
            if 'family' in event.keys() and event['family'] == socket.AF_INET:
                ipport = '%s:%d' % (common.get_v4_addr_str(event['v4addr']),
                                    event['sport'])
                current_syscall['filename'] = ipport
            else:
                current_syscall['filename'] = 'socket'
        elif name in sv.SyscallConsts.NET_OPEN_SYSCALLS:
            current_syscall['filename'] = 'socket'
        elif name == 'dup2':
            newfd = event['newfd']
            oldfd = event['oldfd']
            if newfd in proc.fds.keys():
                self._close_fd(proc, newfd)
            if oldfd in proc.fds.keys():
                current_syscall['filename'] = proc.fds[oldfd].filename
                current_syscall['fdtype'] = proc.fds[oldfd].fdtype
            else:
                current_syscall['filename'] = ''
        elif name == 'fcntl':
            # F_DUPsv.FD
            if event['cmd'] != 0:
                return
            oldfd = event['fd']
            if oldfd in proc.fds.keys():
                current_syscall['filename'] = proc.fds[oldfd].filename
                current_syscall['fdtype'] = proc.fds[oldfd].fdtype
            else:
                current_syscall['filename'] = ''

        if name in sv.SyscallConsts.NET_OPEN_SYSCALLS and \
                'family' in event.keys():
            family = event['family']
            current_syscall['family'] = family
        else:
            family = socket.AF_UNSPEC
            current_syscall['family'] = family

        current_syscall['name'] = name
        current_syscall['start'] = event.timestamp
        current_syscall['fdtype'] = self._get_fd_type(name, family)

    def _track_close(self, name, proc, event, cpu):
        fd = event['fd']
        if fd not in proc.fds:
            return

        tid = self._state.tids[cpu.current_tid]
        tid.current_syscall = {}
        current_syscall = tid.current_syscall
        current_syscall['filename'] = proc.fds[fd].filename
        current_syscall['name'] = name
        current_syscall['start'] = event.timestamp

        self._close_fd(proc, fd)

    def _close_fd(self, proc, fileno):
        filename = proc.fds[fileno].filename
        if filename not in sv.SyscallConsts.GENERIC_NAMES \
           and filename in proc.closed_fds:
            fd = proc.closed_fds[filename]
            fd.net_read += proc.fds[fileno].net_read
            fd.disk_read += proc.fds[fileno].disk_read
            fd.net_write += proc.fds[fileno].net_write
            fd.disk_write += proc.fds[fileno].disk_write
        else:
            proc.closed_fds[filename] = proc.fds[fileno]

        del proc.fds[fileno]

    def _track_sync(self, event):
        name = common.get_syscall_name(event)
        cpu_id = event['cpu_id']

        if cpu_id not in self._state.cpus:
            return

        cpu = self._state.cpus[cpu_id]
        if cpu.current_tid is None:
            return

        proc = self._state.tids[cpu.current_tid]
        self._state.pending_syscalls.append(proc)
        # if it's a thread, we want the parent
        if proc.pid is not None and proc.tid != proc.pid:
            proc = self._state.tids[proc.pid]

        current_syscall = proc.current_syscall
        current_syscall['name'] = name
        current_syscall['start'] = event.timestamp
        if name != 'sync':
            fileno = event['fd']
            fd = self._get_fd(proc, fileno, event)
            current_syscall['fd'] = fd
            current_syscall['filename'] = fd.filename

    def _track_read_write_return(self, name, ret, cpu):
        if ret < 0:
            # TODO: track errors
            return
        proc = self._state.tids[cpu.current_tid]
        # if it's a thread, we want the parent
        if proc.pid is not None and proc.tid != proc.pid:
            proc = self._state.tids[proc.pid]
        current_syscall = self._state.tids[cpu.current_tid].current_syscall
        if name in ['splice', 'sendfile64']:
            self.read_append(current_syscall['fd_in'], proc, ret,
                             current_syscall['iorequest'])
            self.write_append(current_syscall['fd_out'], proc, ret,
                              current_syscall['iorequest'])
        elif name in sv.SyscallConsts.READ_SYSCALLS:
            if ret > 0:
                self.read_append(current_syscall['fd'], proc, ret,
                                 current_syscall['iorequest'])
        elif name in sv.SyscallConsts.WRITE_SYSCALLS:
            if ret > 0:
                self.write_append(current_syscall['fd'], proc, ret,
                                  current_syscall['iorequest'])

    def _track_rw_latency(self, event):
        cpu_id = event['cpu_id']
        cpu = self._state.cpus[cpu_id]
        proc = self._state.tids[cpu.current_tid]
        current_syscall = proc.current_syscall

        rq = current_syscall['iorequest']
        rq.begin = current_syscall['start']
        rq.end = event.timestamp
        rq.duration = rq.end - rq.begin
        rq.proc = proc

        if 'fd' in current_syscall:
            rq.fd = current_syscall['fd']
        elif 'fd_in' in current_syscall:
            rq.fd = current_syscall['fd_in']

        # pages written during the latency
        if 'pages_written' in current_syscall:
            rq.page_written = current_syscall['pages_written']
        # allocated pages during the latency
        if 'pages_allocated' in current_syscall:
            rq.page_alloc = current_syscall['pages_allocated']
        if 'page_free' in current_syscall:
            rq.page_free = current_syscall['page_free']
        # wakeup_kswapd during the latency
        if 'wakeup_kswapd' in current_syscall:
            rq.woke_kswapd = True

        rq.fd.iorequests.append(rq)

    def _add_tid_fd(self, event):
        cpu = self._state.cpus[event['cpu_id']]
        ret = event['ret']
        proc = self._state.tids[cpu.current_tid]
        # set current syscall to that of proc even if it's a thread
        current_syscall = proc.current_syscall

        # if it's a thread, we want the parent
        if proc.pid is not None and proc.tid != proc.pid:
            proc = self._state.tids[proc.pid]

        filename = current_syscall['filename']
        if filename not in sv.SyscallConsts.GENERIC_NAMES \
           and filename in proc.closed_fds:
            fd = proc.closed_fds[filename]
        else:
            fd = sv.FD()
            fd.filename = filename
            if current_syscall['name'] in sv.SyscallConsts.NET_OPEN_SYSCALLS:
                fd.family = current_syscall['family']
                if fd.family in sv.SyscallConsts.INET_FAMILIES:
                    fd.fdtype = sv.FDType.net

        if ret >= 0:
            fd.fd = ret
        else:
            return

        if 'cloexec' in current_syscall.keys():
            fd.cloexec = True

        proc.fds[fd.fd] = fd
        proc.track_chrono_fd(fd.fd, fd.filename, fd.fdtype, event.timestamp)

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
                    parent_proc = sv.Process(proc.pid, proc.proc, proc.comm)
                    self._state.tids[parent_proc.pid] = parent_proc

    def _get_fd(self, proc, fileno, event):
        if fileno not in proc.fds:
            fd = sv.FD()
            fd.fd = fileno
            fd.filename = 'unknown (origin not found)'
            proc.fds[fileno] = fd
        else:
            fd = proc.fds[fileno]

        proc.track_chrono_fd(fileno, fd.filename, fd.fdtype, event.timestamp)

        return fd

    def _get_fd_type(self, name, family):
        if name in sv.SyscallConsts.NET_OPEN_SYSCALLS:
            if family in sv.SyscallConsts.INET_FAMILIES:
                return sv.FDType.net
            if family in sv.SyscallConsts.DISK_FAMILIES:
                return sv.FDType.disk

        if name in sv.SyscallConsts.DISK_OPEN_SYSCALLS:
            return sv.FDType.disk

        return sv.FDType.unknown

    def read_append(self, fd, proc, count, rq):
        rq.operation = sv.IORequest.OP_READ
        rq.size = count
        if fd.fdtype in [sv.FDType.net, sv.FDType.maybe_net]:
            fd.net_read += count
            proc.net_read += count
        elif fd.fdtype == sv.FDType.disk:
            fd.disk_read += count
            proc.disk_read += count
        else:
            fd.unk_read += count
            proc.unk_read += count
        fd.read += count
        proc.read += count

    def write_append(self, fd, proc, count, rq):
        rq.operation = sv.IORequest.OP_WRITE
        rq.size = count
        if fd.fdtype in [sv.FDType.net, sv.FDType.maybe_net]:
            fd.net_write += count
            proc.net_write += count
        elif fd.fdtype == sv.FDType.disk:
            fd.disk_write += count
            proc.disk_write += count
        else:
            fd.unk_write += count
            proc.unk_write += count
        fd.write += count
        proc.write += count
