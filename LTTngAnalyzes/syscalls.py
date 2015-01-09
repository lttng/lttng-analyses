from LTTngAnalyzes.common import FDType, FD, ns_to_hour_nsec, Syscall, \
    O_CLOEXEC, get_v4_addr_str, Process, IORequest
import socket
import operator


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


class Syscalls():
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
    # generic names assigned to special FDs, don't try to match these in the
    # closed_fds dict
    GENERIC_NAMES = ["unknown", "socket"]

    def get_syscall_category(name):
        """Receives a syscall name and returns an enum value
        representing its IO category (open, close, read, or write)"

        This is used to produce json data for visualization"""

        if name in Syscalls.OPEN_SYSCALLS:
            return IOCategory.opn
        if name in Syscalls.CLOSE_SYSCALLS:
            return IOCategory.close
        if name in Syscalls.READ_SYSCALLS:
            return IOCategory.read
        if name in Syscalls.WRITE_SYSCALLS:
            return IOCategory.write

        return IOCategory.invalid

    def get_fd_type(name, family):
        if name in Syscalls.NET_OPEN_SYSCALLS:
            if family in Syscalls.INET_FAMILIES:
                return FDType.net
            if family in Syscalls.DISK_FAMILIES:
                return FDType.disk

        if name in Syscalls.DISK_OPEN_SYSCALLS:
            return FDType.disk

        return FDType.unknown

    def __init__(self, cpus, tids, syscalls, dirty_pages={}, names=None,
                 latency=-1, latency_hist=None, seconds=False):
        self.cpus = cpus
        self.tids = tids
        self.syscalls = syscalls
        self.syscalls["total"] = 0
        self.dirty_pages = dirty_pages
        self.names = names
        self.latency = latency
        self.latency_hist = latency_hist
        self.seconds = seconds

    def global_syscall_entry(self, name):
        if name not in self.syscalls:
            s = Syscall()
            s.name = name
            s.count = 0
            self.syscalls[name] = s
        else:
            s = self.syscalls[name]
        s.count += 1
        self.syscalls["total"] += 1

    def per_tid_syscall_entry(self, name, cpu_id):
        # we don't know which process is currently on this CPU
        if cpu_id not in self.cpus:
            return
        c = self.cpus[cpu_id]
        if c.current_tid == -1:
            return
        t = self.tids[c.current_tid]
        t.total_syscalls += 1
        if name not in t.syscalls:
            s = Syscall()
            s.name = name
            t.syscalls[name] = s
        else:
            s = t.syscalls[name]
        s.count += 1

    def track_open(self, name, proc, event, cpu):
        self.tids[cpu.current_tid].current_syscall = {}
        current_syscall = self.tids[cpu.current_tid].current_syscall
        if name in Syscalls.DISK_OPEN_SYSCALLS:
            current_syscall["filename"] = event["filename"]
            if event["flags"] & O_CLOEXEC == O_CLOEXEC:
                current_syscall["cloexec"] = 1
        elif name in ["sys_accept", "syscall_entry_accept"]:
            if "family" in event.keys() and event["family"] == socket.AF_INET:
                ipport = "%s:%d" % (get_v4_addr_str(event["v4addr"]),
                                    event["sport"])
                current_syscall["filename"] = ipport
            else:
                current_syscall["filename"] = "socket"
        elif name in Syscalls.NET_OPEN_SYSCALLS:
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
            # F_DUPFD
            if event["cmd"] != 0:
                return
            oldfd = event["fd"]
            if oldfd in proc.fds.keys():
                current_syscall["filename"] = proc.fds[oldfd].filename
                current_syscall["fdtype"] = proc.fds[oldfd].fdtype
            else:
                current_syscall["filename"] = ""

        if name in Syscalls.NET_OPEN_SYSCALLS and "family" in event.keys():
            family = event["family"]
            current_syscall["family"] = family
        else:
            family = socket.AF_UNSPEC
            current_syscall["family"] = family

        current_syscall["name"] = name
        current_syscall["start"] = event.timestamp
        current_syscall["fdtype"] = Syscalls.get_fd_type(name, family)

    def close_fd(self, proc, fd):
        filename = proc.fds[fd].filename
        if filename not in Syscalls.GENERIC_NAMES \
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
#        print("Close FD %s in %d (%d, %d, %d, %d)" %
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
        if t.pid == -1 and "pid" in event.keys():
            t.pid = event["pid"]
            p = Process()
            p.tid = t.pid
            p.pid = t.pid
            p.comm = t.comm
            self.tids[p.pid] = p
        # if it's a thread, we want the parent
        if t.pid != -1 and t.tid != t.pid:
            t = self.tids[t.pid]
        if name in Syscalls.OPEN_SYSCALLS:
            self.track_open(name, t, event, c)
        elif name in Syscalls.CLOSE_SYSCALLS:
            ret_string = "%s %s(%d)" % (ns_to_hour_nsec(event.timestamp),
                                        name, event["fd"])
            self.track_close(name, t, event, c)
        # when a connect occurs, no new FD is returned, but we can fix
        # the "filename" if we have the destination info
        elif name in ["sys_connect", "syscall_entry_connect"] \
                and "family" in event.keys():
            if event["family"] == socket.AF_INET:
                fd = self.get_fd(t, event["fd"])
                ipport = "%s:%d" % (get_v4_addr_str(event["v4addr"]),
                                    event["dport"])
                fd.filename = ipport
        return ret_string

    def get_fd(self, proc, fd):
        if fd not in proc.fds.keys():
            f = FD()
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
        if name not in Syscalls.GENERIC_NAMES \
           and name in t.closed_fds.keys():
            fd = t.closed_fds[name]
            fd.open += 1
        else:
            fd = FD()
            fd.filename = name
            if current_syscall["name"] in Syscalls.NET_OPEN_SYSCALLS:
                fd.family = current_syscall["family"]
                if fd.family in Syscalls.INET_FAMILIES:
                    fd.fdtype = FDType.net
            fd.open = 1
        if ret >= 0:
            fd.fd = ret
        else:
            return
#        if fd.fd in t.fds.keys():
#            print("%lu : FD %d in tid %d was already there, untracked close" %
#                    (event.timestamp, fd.fd, t.tid))
        if "cloexec" in current_syscall.keys():
            fd.cloexec = 1
        t.fds[fd.fd] = fd
        # print("%lu : %s opened %s (%d times)" % (event.timestamp, t.comm,
        #     fd.filename, fd.open))

    def read_append(self, fd, proc, count, rq):
        rq.operation = IORequest.OP_READ
        rq.size = count
        if fd.fdtype in [FDType.net, FDType.maybe_net]:
            fd.net_read += count
            proc.net_read += count
        elif fd.fdtype == FDType.disk:
            fd.disk_read += count
            proc.disk_read += count
        else:
            fd.unk_read += count
            proc.unk_read += count
        fd.read += count
        proc.read += count

    def write_append(self, fd, proc, count, rq):
        rq.operation = IORequest.OP_WRITE
        rq.size = count
        if fd.fdtype in [FDType.net, FDType.maybe_net]:
            fd.net_write += count
            proc.net_write += count
        elif fd.fdtype == FDType.disk:
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
        elif name in Syscalls.READ_SYSCALLS:
            if ret > 0:
                self.read_append(current_syscall["fd"], proc, ret,
                                 current_syscall["iorequest"])
        elif name in Syscalls.WRITE_SYSCALLS:
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

    def track_rw_latency(self, name, ret, c, ts, started, event):
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
        if name in Syscalls.SYNC_SYSCALLS:
#            self.syscall_clear_pages(event, name, fd, current_syscall,
#                                     self.tids[c.current_tid])
            if "pages_cleared" in current_syscall.keys():
                rq.page_cleared = len(current_syscall["pages_cleared"])

    def entry(self, event):
        name = event.name
        ret_string = ""
        cpu_id = event["cpu_id"]
        self.global_syscall_entry(name)
        self.per_tid_syscall_entry(name, cpu_id)
        ret_string = self.track_fds(name, event, cpu_id)
        if name in Syscalls.READ_SYSCALLS or name in Syscalls.WRITE_SYSCALLS:
            self.track_read_write(name, event, cpu_id)
        if name in Syscalls.SYNC_SYSCALLS:
            self.track_sync(name, event, cpu_id)
        return ret_string

    def exit(self, event, started):
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
        current_syscall["iorequest"] = IORequest()
        current_syscall["iorequest"].iotype = IORequest.IO_SYSCALL
        current_syscall["iorequest"].name = name
        if name in Syscalls.OPEN_SYSCALLS:
            self.add_tid_fd(event, c)
            ret_string = "%s %s(%s, fd = %d)" % (
                ns_to_hour_nsec(current_syscall["start"]),
                name, current_syscall["filename"], ret)
            if ret < 0:
                return ret_string
            t = self.tids[c.current_tid]
            current_syscall["fd"] = self.get_fd(t, ret)
            current_syscall["count"] = 0
            current_syscall["fd"].fdtype = current_syscall["fdtype"]
            current_syscall["iorequest"].operation = IORequest.OP_OPEN
            self.track_rw_latency(name, ret, c,
                                  event.timestamp, started, event)
        elif name in Syscalls.READ_SYSCALLS or name in Syscalls.WRITE_SYSCALLS:
            self.track_read_write_return(name, ret, c)
            self.track_rw_latency(name, ret, c, event.timestamp,
                                  started, event)
        elif name in Syscalls.SYNC_SYSCALLS:
            current_syscall["iorequest"].operation = IORequest.OP_SYNC
            self.track_rw_latency(name, ret, c, event.timestamp,
                                  started, event)
        self.tids[c.current_tid].current_syscall = {}
        return ret_string

    def wb_pages(self, event):
        """writeback_pages_written"""
        for c in self.cpus.values():
            if c.current_tid <= 0:
                continue
            current_syscall = self.tids[c.current_tid].current_syscall
            if len(current_syscall.keys()) == 0:
                continue
            current_syscall["pages_written"] = event["pages"]

    def wakeup_kswapd(self, event):
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

    def page_free(self, event):
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
