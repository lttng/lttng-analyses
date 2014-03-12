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
        if filename in proc.closed_fds.keys():
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

    def add_tid_fd(self, event, cpu):
        ret = event["ret"]
        t = self.tids[cpu.current_tid]
        # if it's a thread, we want the parent
        if t.pid != -1 and t.tid != t.pid:
            t = self.tids[t.pid]
        name = cpu.current_syscall["filename"]
        if name in t.closed_fds.keys():
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
        if fd.fd in t.fds.keys():
            print("%lu : FD %d in tid %d was already there, untracked close" %
                    (event.timestamp, fd.fd, t.tid))
        if "cloexec" in cpu.current_syscall.keys():
            fd.cloexec = 1
        t.fds[fd.fd] = fd
        #print("%lu : %s opened %s (%d times)" % (event.timestamp, t.comm,
        #    fd.filename, fd.open))

    def entry(self, event):
        name = event.name
        cpu_id = event["cpu_id"]
        self.global_syscall_entry(name)
        self.per_tid_syscall_entry(name, cpu_id)
        self.track_fds(name, event, cpu_id)

    def exit(self, event):
        cpu_id = event["cpu_id"]
        if not cpu_id in self.cpus:
            return
        c = self.cpus[cpu_id]
        if c.current_tid == -1:
            return
        if len(c.current_syscall.keys()) == 0:
            return
        if c.current_syscall["name"] in self.open_syscalls:
            self.add_tid_fd(event, c)
        c.current_syscall = {}
