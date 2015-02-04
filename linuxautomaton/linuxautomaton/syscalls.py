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
import operator
from linuxautomaton import sp, sv, common
from babeltrace import CTFScope


class IOCategory():
    """Defines an enumeration mapping IO categories to integer values.
    Used mainly to export syscall metadata (to JSON)."""

    invalid = 0
    # Can't use open as a name given that is is a built-in function
    # TODO: find less stupid name
    opn = 1
    close = 2
    read = 3
    write = 4


class SyscallsStateProvider(sp.StateProvider):
    def __init__(self, state):
        self.state = state
        self.cpus = state.cpus
        self.tids = state.tids
        self.syscalls = state.syscalls
        self.pending_syscalls = state.pending_syscalls
        self.syscalls["total"] = 0
        self.dirty_pages = state.dirty_pages
        cbs = {
            'syscall_entry': self._process_syscall_entry,
            'syscall_exit': self._process_syscall_exit,
            'writeback_pages_written': self._process_writeback_pages_written,
            'mm_vmscan_wakeup_kswapd': self._process_mm_vmscan_wakeup_kswapd,
            'mm_page_free': self._process_mm_page_free,
        }
        self._register_cbs(cbs)

    def process_event(self, ev):
        self._process_event_cb(ev)

    def get_syscall_category(self, name):
        """Receives a syscall name and returns an enum value
        representing its IO category (open, close, read, or write)"

        This is used to produce json data for visualization"""

        if name in sv.SyscallConsts.OPEN_SYSCALLS:
            return IOCategory.opn
        if name in sv.SyscallConsts.CLOSE_SYSCALLS:
            return IOCategory.close
        if name in sv.SyscallConsts.READ_SYSCALLS:
            return IOCategory.read
        if name in sv.SyscallConsts.WRITE_SYSCALLS:
            return IOCategory.write

        return IOCategory.invalid

    def get_fd_type(self, name, family):
        if name in sv.SyscallConsts.NET_OPEN_SYSCALLS:
            if family in sv.SyscallConsts.INET_FAMILIES:
                return sv.FDType.net
            if family in sv.SyscallConsts.DISK_FAMILIES:
                return sv.FDType.disk

        if name in sv.SyscallConsts.DISK_OPEN_SYSCALLS:
            return sv.FDType.disk

        return sv.FDType.unknown

    def global_syscall_entry(self, name):
        if name not in self.syscalls:
            s = sv.Syscall()
            s.name = name
            s.count = 0
            self.syscalls[name] = s
        else:
            s = self.syscalls[name]
        s.count += 1
        self.syscalls["total"] += 1

    def per_tid_syscall_entry(self, name, cpu_id, event):
        # we don't know which process is currently on this CPU
        if cpu_id not in self.cpus:
            return
        c = self.cpus[cpu_id]
        if c.current_tid == -1:
            return
        t = self.tids[c.current_tid]
        t.total_syscalls += 1
        if name not in t.syscalls:
            s = sv.Syscall()
            s.name = name
            t.syscalls[name] = s
        else:
            s = t.syscalls[name]
        s.count += 1
        current_syscall = t.current_syscall
        current_syscall["name"] = name
        current_syscall["start"] = event.timestamp

    def track_open(self, name, proc, event, cpu):
        self.tids[cpu.current_tid].current_syscall = {}
        current_syscall = self.tids[cpu.current_tid].current_syscall
        if name in sv.SyscallConsts.DISK_OPEN_SYSCALLS:
            current_syscall["filename"] = event["filename"]
            if event["flags"] & common.O_CLOEXEC == common.O_CLOEXEC:
                current_syscall["cloexec"] = 1
        elif name in ["sys_accept", "syscall_entry_accept"]:
            if "family" in event.keys() and event["family"] == socket.AF_INET:
                ipport = "%s:%d" % (common.get_v4_addr_str(event["v4addr"]),
                                    event["sport"])
                current_syscall["filename"] = ipport
            else:
                current_syscall["filename"] = "socket"
        elif name in sv.SyscallConsts.NET_OPEN_SYSCALLS:
            current_syscall["filename"] = "socket"
        elif name in ["sys_dup2", "syscall_entry_dup2"]:
            newfd = event["newfd"]
            oldfd = event["oldfd"]
            if newfd in proc.fds.keys():
                self.close_fd(proc, newfd)
            if oldfd in proc.fds.keys():
                current_syscall["filename"] = proc.fds[oldfd].filename
                current_syscall["fdtype"] = proc.fds[oldfd].fdtype
            else:
                current_syscall["filename"] = ""
        elif name in ["sys_fcntl", "syscall_entry_fcntl"]:
            # F_DUPsv.FD
            if event["cmd"] != 0:
                return
            oldfd = event["fd"]
            if oldfd in proc.fds.keys():
                current_syscall["filename"] = proc.fds[oldfd].filename
                current_syscall["fdtype"] = proc.fds[oldfd].fdtype
            else:
                current_syscall["filename"] = ""

        if name in sv.SyscallConsts.NET_OPEN_SYSCALLS and \
                "family" in event.keys():
            family = event["family"]
            current_syscall["family"] = family
        else:
            family = socket.AF_UNSPEC
            current_syscall["family"] = family

        current_syscall["name"] = name
        current_syscall["start"] = event.timestamp
        current_syscall["fdtype"] = self.get_fd_type(name, family)

    def close_fd(self, proc, fd):
        filename = proc.fds[fd].filename
        if filename not in sv.SyscallConsts.GENERIC_NAMES \
           and filename in proc.closed_fds.keys():
            f = proc.closed_fds[filename]
            f.close += 1
            f.net_read += proc.fds[fd].net_read
            f.disk_read += proc.fds[fd].disk_read
            f.net_write += proc.fds[fd].net_write
            f.disk_write += proc.fds[fd].disk_write
        else:
            proc.closed_fds[filename] = proc.fds[fd]
            proc.closed_fds[filename].close = 1
#        print("Close sv.FD %s in %d (%d, %d, %d, %d)" %
#                (filename, proc.tid, proc.fds[fd].read, proc.fds[fd].write,
#                    proc.fds[fd].open, proc.fds[fd].close))
        proc.fds.pop(fd, None)

    def track_close(self, name, proc, event, cpu):
        fd = event["fd"]
        if fd not in proc.fds.keys():
            return

        tid = self.tids[cpu.current_tid]
        tid.current_syscall = {}
        current_syscall = tid.current_syscall
        current_syscall["filename"] = proc.fds[fd].filename
        current_syscall["name"] = name
        current_syscall["start"] = event.timestamp

        self.close_fd(proc, fd)

    def _fix_context_pid(self, event, t):
        for context in event.field_list_with_scope(
                CTFScope.STREAM_EVENT_CONTEXT):
            if context != "pid":
                continue
            # make sure the "pid" field is not also in the event
            # payload, otherwise we might clash
            for context in event.field_list_with_scope(
                    CTFScope.EVENT_FIELDS):
                if context == "pid":
                    return
            if t.pid == -1:
                t.pid == event["pid"]
                if event["pid"] != t.tid:
                    t.pid = event["pid"]
                    p = sv.Process()
                    p.tid = t.pid
                    p.pid = t.pid
                    p.comm = t.comm
                    self.tids[p.pid] = p

    def track_fds(self, name, event, cpu_id):
        # we don't know which process is currently on this CPU
        ret_string = ""
        if cpu_id not in self.cpus:
            return
        c = self.cpus[cpu_id]
        if c.current_tid == -1:
            return
        t = self.tids[c.current_tid]
        # check if we can fix the pid from a context
        self._fix_context_pid(event, t)
        # if it's a thread, we want the parent
        if t.pid != -1 and t.tid != t.pid:
            t = self.tids[t.pid]
        if name in sv.SyscallConsts.OPEN_SYSCALLS:
            self.track_open(name, t, event, c)
        elif name in sv.SyscallConsts.CLOSE_SYSCALLS:
            ret_string = "%s %s(%d)" % \
                (common.ns_to_hour_nsec(event.timestamp),
                 name, event["fd"])
            self.track_close(name, t, event, c)
        # when a connect occurs, no new sv.FD is returned, but we can fix
        # the "filename" if we have the destination info
        elif name in ["sys_connect", "syscall_entry_connect"] \
                and "family" in event.keys():
            if event["family"] == socket.AF_INET:
                fd = self.get_fd(t, event["fd"])
                ipport = "%s:%d" % (common.get_v4_addr_str(event["v4addr"]),
                                    event["dport"])
                fd.filename = ipport
        return ret_string

    def get_fd(self, proc, fd):
        if fd not in proc.fds.keys():
            f = sv.FD()
            f.fd = fd
            f.filename = "unknown (origin not found)"
            proc.fds[fd] = f
        else:
            f = proc.fds[fd]
        return f

    def track_sync(self, name, event, cpu_id):
        # we don't know which process is currently on this CPU
        if cpu_id not in self.cpus:
            return
        c = self.cpus[cpu_id]
        if c.current_tid == -1:
            return
        t = self.tids[c.current_tid]
        self.pending_syscalls.append(t)
        # if it's a thread, we want the parent
        if t.pid != -1 and t.tid != t.pid:
            t = self.tids[t.pid]
        current_syscall = self.tids[c.current_tid].current_syscall
        current_syscall["name"] = name
        current_syscall["start"] = event.timestamp
        if name not in ["sys_sync", "syscall_entry_sync"]:
            fd = event["fd"]
            f = self.get_fd(t, fd)
            current_syscall["fd"] = f
            current_syscall["filename"] = f.filename

    def track_read_write(self, name, event, cpu_id):
        # we don't know which process is currently on this CPU
        if cpu_id not in self.cpus:
            return
        c = self.cpus[cpu_id]
        if c.current_tid == -1:
            return
        t = self.tids[c.current_tid]
        self.pending_syscalls.append(t)
        # if it's a thread, we want the parent
        if t.pid != -1 and t.tid != t.pid:
            t = self.tids[t.pid]
        current_syscall = self.tids[c.current_tid].current_syscall
        current_syscall["name"] = name
        current_syscall["start"] = event.timestamp
        if name in ["sys_splice", "syscall_entry_splice"]:
            current_syscall["fd_in"] = self.get_fd(t, event["fd_in"])
            current_syscall["fd_out"] = self.get_fd(t, event["fd_out"])
            current_syscall["count"] = event["len"]
            current_syscall["filename"] = current_syscall["fd_in"].filename
            return
        elif name in ["sys_sendfile64", "syscall_entry_sendfile64"]:
            current_syscall["fd_in"] = self.get_fd(t, event["in_fd"])
            current_syscall["fd_out"] = self.get_fd(t, event["out_fd"])
            current_syscall["count"] = event["count"]
            current_syscall["filename"] = current_syscall["fd_in"].filename
            return
        fd = event["fd"]
        f = self.get_fd(t, fd)
        current_syscall["fd"] = f
        if name in ["sys_writev", "syscall_entry_writev",
                    "sys_readv", "syscall_entry_readv"]:
            current_syscall["count"] = event["vlen"]
        elif name in ["sys_recvfrom", "syscall_entry_recvfrom"]:
            current_syscall["count"] = event["size"]
        elif name in ["sys_recvmsg", "syscall_entry_recvmsg",
                      "sys_sendmsg", "syscall_entry_sendmsg"]:
            current_syscall["count"] = ""
        elif name in ["sys_sendto", "syscall_entry_sendto"]:
            current_syscall["count"] = event["len"]
        else:
            try:
                current_syscall["count"] = event["count"]
            except:
                print("Missing count argument for syscall",
                      current_syscall["name"])
                current_syscall["count"] = 0

        current_syscall["filename"] = f.filename

    def add_tid_fd(self, event, cpu):
        ret = event["ret"]
        t = self.tids[cpu.current_tid]
        # if it's a thread, we want the parent
        if t.pid != -1 and t.tid != t.pid:
            t = self.tids[t.pid]
        current_syscall = self.tids[cpu.current_tid].current_syscall

        name = current_syscall["filename"]
        if name not in sv.SyscallConsts.GENERIC_NAMES \
           and name in t.closed_fds.keys():
            fd = t.closed_fds[name]
            fd.open += 1
        else:
            fd = sv.FD()
            fd.filename = name
            if current_syscall["name"] in sv.SyscallConsts.NET_OPEN_SYSCALLS:
                fd.family = current_syscall["family"]
                if fd.family in sv.SyscallConsts.INET_FAMILIES:
                    fd.fdtype = sv.FDType.net
            fd.open = 1
        if ret >= 0:
            fd.fd = ret
        else:
            return
        if "cloexec" in current_syscall.keys():
            fd.cloexec = 1
        t.fds[fd.fd] = fd

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

    def track_read_write_return(self, name, ret, cpu):
        if ret < 0:
            # TODO: track errors
            return
        proc = self.tids[cpu.current_tid]
        # if it's a thread, we want the parent
        if proc.pid != -1 and proc.tid != proc.pid:
            proc = self.tids[proc.pid]
        current_syscall = self.tids[cpu.current_tid].current_syscall
        if name in ["sys_splice", "syscall_entry_splice",
                    "sys_sendfile64", "syscall_entry_sendfile64"]:
            self.read_append(current_syscall["fd_in"], proc, ret,
                             current_syscall["iorequest"])
            self.write_append(current_syscall["fd_out"], proc, ret,
                              current_syscall["iorequest"])
        elif name in sv.SyscallConsts.READ_SYSCALLS:
            if ret > 0:
                self.read_append(current_syscall["fd"], proc, ret,
                                 current_syscall["iorequest"])
        elif name in sv.SyscallConsts.WRITE_SYSCALLS:
            if ret > 0:
                self.write_append(current_syscall["fd"], proc, ret,
                                  current_syscall["iorequest"])

    def get_page_queue_stats(self, page_list):
        processes = {}
        for i in page_list:
            procname = i[0].comm
            tid = i[0].tid
            filename = i[2]
            if tid not in processes.keys():
                processes[tid] = {}
                processes[tid]["procname"] = procname
                processes[tid]["count"] = 1
                processes[tid]["files"] = {}
                processes[tid]["files"][filename] = 1
            else:
                processes[tid]["count"] += 1
                if filename not in processes[tid]["files"].keys():
                    processes[tid]["files"][filename] = 1
                else:
                    processes[tid]["files"][filename] += 1
        return processes

    def print_page_table(self, event, pages):
        spaces = (41 + 6) * " "
        for i in pages.keys():
            p = pages[i]
            print("%s %s (%d): %d pages" % (spaces, p["procname"],
                                            i, p["count"]))
            files = sorted(p["files"].items(), key=operator.itemgetter(1),
                           reverse=True)
            for f in files:
                print("%s  - %s : %d pages" % (spaces, f[0], f[1]))

    def syscall_clear_pages(self, event, name, fd, current_syscall, tid):
        cleaned = []
        if name in ["sys_sync", "syscall_entry_sync"]:
            # remove all the pages
            for i in range(len(self.dirty_pages["pages"])):
                cleaned.append(self.dirty_pages["pages"].pop(0))
        else:
            # remove only the pages that belong to a specific proc/fd
            for i in range(len(self.dirty_pages["pages"])):
                proc = self.dirty_pages["pages"][i][0]
                page_fd = self.dirty_pages["pages"][i][3]
                if page_fd == fd and (tid.tid == proc.tid or
                                      tid.pid == proc.pid):
                    cleaned.append(self.dirty_pages["pages"][i])
            for i in cleaned:
                self.dirty_pages["pages"].remove(i)
        if len(cleaned) > 0:
            current_syscall["pages_cleared"] = cleaned

    def track_rw_latency(self, name, ret, c, ts, event):
        current_syscall = self.tids[c.current_tid].current_syscall
        rq = current_syscall["iorequest"]
#       FIXME: useless ?
#        if "start" not in current_syscall.keys():
#            return
        rq.duration = (event.timestamp - current_syscall["start"])
        rq.begin = current_syscall["start"]
        rq.end = event.timestamp
        rq.proc = self.tids[c.current_tid]
        if "fd" in current_syscall.keys():
            rq.fd = current_syscall["fd"]
            r = current_syscall["fd"].iorequests
            r.append(current_syscall["iorequest"])
        elif "fd_in" in current_syscall.keys():
            rq.fd = current_syscall["fd_in"]
        # pages written during the latency
        if "pages_written" in current_syscall.keys():
            rq.page_written = current_syscall["pages_written"]
        # dirty buffers during the latency
        if "dirty" in current_syscall.keys():
            rq.dirty = current_syscall["dirty"]
        # alloc pages during the latency
        if "alloc" in current_syscall.keys():
            rq.page_alloc = current_syscall["alloc"]
        # wakeup_kswapd during the latency
        if "page_free" in current_syscall.keys():
            rq.page_free = current_syscall["page_free"]
        if "wakeup_kswapd" in current_syscall.keys():
            rq.woke_kswapd = True
        if name in sv.SyscallConsts.SYNC_SYSCALLS:
#            self.syscall_clear_pages(event, name, fd, current_syscall,
#                                     self.tids[c.current_tid])
            if "pages_cleared" in current_syscall.keys():
                rq.page_cleared = len(current_syscall["pages_cleared"])

    def _per_tid_syscall_exit(self, name, ret, event, c):
        t = self.tids[c.current_tid]
        s = sv.SyscallEvent()
        s.ret = ret
        s.entry_ts = t.current_syscall["start"]
        s.exit_ts = event.timestamp
        s.duration = s.exit_ts - s.entry_ts
        t_syscall = t.syscalls[name]
        if t_syscall.min is None or t_syscall.min > s.duration:
            t_syscall.min = s.duration
        if t_syscall.max < s.duration:
            t_syscall.max = s.duration
        t_syscall.total_duration += s.duration
        t_syscall.rq.append(s)

    def _process_syscall_entry(self, event):
        name = event.name
        ret_string = ""
        cpu_id = event["cpu_id"]
        self.global_syscall_entry(name)
        self.per_tid_syscall_entry(name, cpu_id, event)
        ret_string = self.track_fds(name, event, cpu_id)
        if name in sv.SyscallConsts.READ_SYSCALLS or \
                name in sv.SyscallConsts.WRITE_SYSCALLS:
            self.track_read_write(name, event, cpu_id)
        if name in sv.SyscallConsts.SYNC_SYSCALLS:
            self.track_sync(name, event, cpu_id)
        return ret_string

    def _process_syscall_exit(self, event):
        cpu_id = event["cpu_id"]
        ret_string = ""
        if cpu_id not in self.cpus:
            return
        c = self.cpus[cpu_id]
        if c.current_tid == -1:
            return
        current_syscall = self.tids[c.current_tid].current_syscall
        if len(current_syscall.keys()) == 0:
            return
        name = current_syscall["name"]
        ret = event["ret"]
        self._per_tid_syscall_exit(name, ret, event, c)

        if name not in sv.SyscallConsts.IO_SYSCALLS:
            return

        current_syscall["iorequest"] = sv.IORequest()
        current_syscall["iorequest"].iotype = sv.IORequest.IO_SYSCALL
        current_syscall["iorequest"].name = name
        if name in sv.SyscallConsts.OPEN_SYSCALLS:
            self.add_tid_fd(event, c)
            ret_string = "%s %s(%s, fd = %d)" % (
                common.ns_to_hour_nsec(current_syscall["start"]),
                name, current_syscall["filename"], ret)
            if ret < 0:
                return ret_string
            t = self.tids[c.current_tid]
            current_syscall["fd"] = self.get_fd(t, ret)
            current_syscall["count"] = 0
            current_syscall["fd"].fdtype = current_syscall["fdtype"]
            current_syscall["iorequest"].operation = sv.IORequest.OP_OPEN
            self.track_rw_latency(name, ret, c,
                                  event.timestamp, event)
        elif name in sv.SyscallConsts.READ_SYSCALLS or \
                name in sv.SyscallConsts.WRITE_SYSCALLS:
            self.track_read_write_return(name, ret, c)
            self.track_rw_latency(name, ret, c, event.timestamp, event)
        elif name in sv.SyscallConsts.SYNC_SYSCALLS:
            current_syscall["iorequest"].operation = sv.IORequest.OP_SYNC
            self.track_rw_latency(name, ret, c, event.timestamp, event)
            if name in ["sys_sync", "syscall_entry_sync"]:
                t = self.tids[c.current_tid]
                t.iorequests.append(current_syscall["iorequest"])
        self.tids[c.current_tid].current_syscall = {}
        if self.tids[c.current_tid] in self.pending_syscalls:
            self.pending_syscalls.remove(self.tids[c.current_tid])
        return ret_string

    def _process_writeback_pages_written(self, event):
        """writeback_pages_written"""
        for c in self.cpus.values():
            if c.current_tid <= 0:
                continue
            current_syscall = self.tids[c.current_tid].current_syscall
            if len(current_syscall.keys()) == 0:
                continue
            current_syscall["pages_written"] = event["pages"]

    def _process_mm_vmscan_wakeup_kswapd(self, event):
        """mm_vmscan_wakeup_kswapd"""
        cpu_id = event["cpu_id"]
        if cpu_id not in self.cpus:
            return
        c = self.cpus[cpu_id]
        if c.current_tid == -1:
            return
        current_syscall = self.tids[c.current_tid].current_syscall
        if len(current_syscall.keys()) == 0:
            return
        current_syscall["wakeup_kswapd"] = 1

    def _process_mm_page_free(self, event):
        """mm_page_free"""
        for c in self.cpus.values():
            if c.current_tid <= 0:
                continue
            p = self.tids[c.current_tid]
            # if the current process is kswapd0, we need to
            # attribute the page freed to the process that
            # woke it up.
            if p.comm == "kswapd0" and p.prev_tid > 0:
                p = self.tids[p.prev_tid]
            current_syscall = p.current_syscall
            if len(current_syscall.keys()) == 0:
                continue
            if "wakeup_kswapd" in current_syscall.keys():
                if "page_free" in current_syscall.keys():
                    current_syscall["page_free"] += 1
                else:
                    current_syscall["page_free"] = 1
