from LTTngAnalyzes.common import *

class Syscalls():
    def __init__(self, cpus, tids, syscalls):
        self.cpus = cpus
        self.tids = tids
        self.syscalls = syscalls
        # list of syscalls that open a FD (in the exit_syscall event)
        self.open_syscalls = ["sys_open", "sys_openat", "sys_accept",
                "sys_fcntl", "sys_socket", "sys_dup2"]
        # list of syscalls that close a FD (in the "fd =" field)
        self.close_syscalls = ["sys_close"]
        # list of syscall that read on a FD, value in the exit_syscall following
        self.read_syscalls = ["sys_read", "sys_recvmsg", "sys_recvfrom",
                "sys_splice", "sys_readv"]
        # list of syscall that write on a FD, value in the exit_syscall following
        self.write_syscalls = ["sys_write", "sys_sendmsg" "sys_sendto", "sys_writev"]
        # generic names assigned to special FDs, don't try to match these in the
        # closed_fds dict
        self.generic_names = ["unknown", "socket"]

    def global_syscall_entry(self, name):
        if not name in self.syscalls:
            s = Syscall()
            s.name = name
            s.count = 0
            self.syscalls[name] = s
        else:
            s = self.syscalls[name]
        s.count += 1

    def per_tid_syscall_entry(self, name, cpu_id):
        # we don't know which process is currently on this CPU
        if not cpu_id in self.cpus:
            return
        c = self.cpus[cpu_id]
        if c.current_tid == -1:
            return
        t = self.tids[c.current_tid]
        if not name in t.syscalls:
            s = Syscall()
            s.name = name
            t.syscalls[name] = s
        else:
            s = t.syscalls[name]
        s.count += 1

    def track_open(self, name, proc, event, cpu):
        cpu.current_syscall = {}
        if name in ["sys_open", "sys_openat"]:
            cpu.current_syscall["filename"] = event["filename"]
            if event["flags"] & O_CLOEXEC == O_CLOEXEC:
                cpu.current_syscall["cloexec"] = 1
        elif name in ["sys_accept", "sys_socket"]:
            cpu.current_syscall["filename"] = "socket"
        elif name in ["sys_dup2"]:
            newfd = event["newfd"]
            oldfd = event["oldfd"]
            if newfd in proc.fds.keys():
                self.close_fd(proc, newfd)
            if oldfd in proc.fds.keys():
                cpu.current_syscall["filename"] = proc.fds[oldfd].filename
            else:
                cpu.current_syscall["filename"] = ""
        elif name in ["sys_fcntl"]:
            # F_DUPFD
            if event["cmd"] != 0:
                return
            oldfd = event["fd"]
            if oldfd in proc.fds.keys():
                cpu.current_syscall["filename"] = proc.fds[oldfd].filename
            else:
                cpu.current_syscall["filename"] = ""
        cpu.current_syscall["name"] = name

    def close_fd(self, proc, fd):
        filename = proc.fds[fd].filename
        if filename not in self.generic_names and filename in proc.closed_fds.keys():
            f = proc.closed_fds[filename]
            f.close += 1
            f.read += proc.fds[fd].read
            f.write += proc.fds[fd].write
        else:
            proc.closed_fds[filename] = proc.fds[fd]
            proc.closed_fds[filename].close = 1
#        print("Close FD %s in %d (%d, %d, %d, %d)" %
#                (filename, proc.tid, proc.fds[fd].read, proc.fds[fd].write,
#                    proc.fds[fd].open, proc.fds[fd].close))
        proc.fds.pop(fd, None)

    def track_close(self, name, proc, event, cpu):
        fd = event["fd"]
        if not fd in proc.fds.keys():
#            print("%lu : Closing FD %d in %d without open" %
#                    (event.timestamp, fd, proc.tid))
            return
        self.close_fd(proc, fd)

    def track_fds(self, name, event, cpu_id):
        # we don't know which process is currently on this CPU
        if not cpu_id in self.cpus:
            return
        c = self.cpus[cpu_id]
        if c.current_tid == -1:
            return
        t = self.tids[c.current_tid]
        # if it's a thread, we want the parent
        if t.pid != -1 and t.tid != t.pid:
            t = self.tids[t.pid]
        if name in self.open_syscalls:
            self.track_open(name, t, event, c)
        elif name in self.close_syscalls:
            self.track_close(name, t, event, c)

    def get_fd(self, proc, fd):
        if fd not in proc.fds.keys():
            f = FD()
            f.fd = fd
            f.name = "unknown (origin not found)"
            proc.fds[fd] = f
        else:
            f = proc.fds[fd]
        return f

    def track_read_write(self, name, event, cpu_id):
        # we don't know which process is currently on this CPU
        if not cpu_id in self.cpus:
            return
        c = self.cpus[cpu_id]
        if c.current_tid == -1:
            return
        t = self.tids[c.current_tid]
        # if it's a thread, we want the parent
        if t.pid != -1 and t.tid != t.pid:
            t = self.tids[t.pid]
        c.current_syscall["name"] = name
        if name == "sys_splice":
            c.current_syscall["fd_in"] = self.get_fd(t, event["fd_in"])
            c.current_syscall["fd_out"] = self.get_fd(t, event["fd_out"])
            return
        fd = event["fd"]
        f = self.get_fd(t, fd)
        c.current_syscall["fd"] = f

    def add_tid_fd(self, event, cpu):
        ret = event["ret"]
        t = self.tids[cpu.current_tid]
        # if it's a thread, we want the parent
        if t.pid != -1 and t.tid != t.pid:
            t = self.tids[t.pid]
        name = cpu.current_syscall["filename"]
        if name not in self.generic_names and name in t.closed_fds.keys():
            fd = t.closed_fds[name]
            fd.open += 1
        else:
            fd = FD()
            fd.filename = name
            fd.open = 1
        if ret > 0:
            fd.fd = ret
        else:
            return
#        if fd.fd in t.fds.keys():
#            print("%lu : FD %d in tid %d was already there, untracked close" %
#                    (event.timestamp, fd.fd, t.tid))
        if "cloexec" in cpu.current_syscall.keys():
            fd.cloexec = 1
        t.fds[fd.fd] = fd
        #print("%lu : %s opened %s (%d times)" % (event.timestamp, t.comm,
        #    fd.filename, fd.open))

    def track_read_write_return(self, name, ret, cpu):
        if ret < 0:
            # TODO: track errors
            return
        proc = self.tids[cpu.current_tid]
        # if it's a thread, we want the parent
        if proc.pid != -1 and proc.tid != proc.pid:
            proc = self.tids[proc.pid]
        if name == "sys_splice":
            cpu.current_syscall["fd_in"].read += ret
            proc.read += ret
            cpu.current_syscall["fd_out"].write += ret
            proc.write += ret
        elif name in self.read_syscalls:
            if ret > 0:
                cpu.current_syscall["fd"].read += ret
                proc.read += ret
        elif name in self.write_syscalls:
            if ret > 0:
                cpu.current_syscall["fd"].write += ret
                proc.write += ret

    def entry(self, event):
        name = event.name
        cpu_id = event["cpu_id"]
        self.global_syscall_entry(name)
        self.per_tid_syscall_entry(name, cpu_id)
        self.track_fds(name, event, cpu_id)
        if name in self.read_syscalls or name in self.write_syscalls:
            self.track_read_write(name, event, cpu_id)

    def exit(self, event):
        cpu_id = event["cpu_id"]
        if not cpu_id in self.cpus:
            return
        c = self.cpus[cpu_id]
        if c.current_tid == -1:
            return
        if len(c.current_syscall.keys()) == 0:
            return
        name = c.current_syscall["name"]
        ret = event["ret"]
        if name in self.open_syscalls:
            self.add_tid_fd(event, c)
        elif name in self.read_syscalls or name in self.write_syscalls:
            self.track_read_write_return(name, ret, c)
        c.current_syscall = {}
