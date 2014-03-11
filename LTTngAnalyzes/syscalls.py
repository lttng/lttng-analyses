from LTTngAnalyzes.common import *

class Syscalls():
    def __init__(self, cpus, tids, syscalls):
        self.cpus = cpus
        self.tids = tids
        self.syscalls = syscalls
        # list of syscalls that open a FD (in the exit_syscall event)
        self.open_syscalls = ["sys_open", "sys_openat"]
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

    def track_open(self, name, event, cpu):
        cpu.current_syscall = {}
        cpu.current_syscall["name"] = name
        if name in ["sys_open", "sys_openat"]:
            cpu.current_syscall["filename"] = event["filename"]

    def track_close(self, name, event, cpu):
        t = self.tids[cpu.current_tid]
        fd = event["fd"]
        if not fd in t.fds.keys():
#            print("%lu : Closing FD %d in %d without open" %
#                    (event.timestamp, fd, t.tid))
            return
        filename = t.fds[fd].filename
        if filename in t.closed_fds.keys():
            f = t.closed_fds[filename]
            f.close += 1
            f.read += t.fds[fd].read
            f.write += t.fds[fd].write
        else:
            t.closed_fds[filename] = t.fds[fd]
            t.closed_fds[filename].close = 1
#        print("Close FD %s in %d (%d, %d, %d, %d)" %
#                (filename, t.tid, t.fds[fd].read, t.fds[fd].write,
#                    t.fds[fd].open, t.fds[fd].close))
        t.fds.pop(fd, None)

    def track_fds(self, name, event, cpu_id):
        # we don't know which process is currently on this CPU
        if not cpu_id in self.cpus:
            return
        c = self.cpus[cpu_id]
        if c.current_tid == -1:
            return
        if name in self.open_syscalls:
            self.track_open(name, event, c)
        elif name in self.close_syscalls:
            self.track_close(name, event, c)

    def add_tid_fd(self, event, cpu):
        ret = event["ret"]
        t = self.tids[cpu.current_tid]
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
#        if fd.fd in t.fds.keys():
#            print("%lu : FD %d in tid %d was already there, untracked close" %
#                    (event.timestamp, fd.fd, t.tid))
        t.fds[fd.fd] = fd
#        print("%lu : %s opened %s (%d times)" % (event.timestamp, t.comm,
#            fd.filename, fd.open))

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
