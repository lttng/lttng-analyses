from LTTngAnalyzes.common import *

class Sched():
    def __init__(self, cpus, tids):
        self.cpus = cpus
        self.tids = tids

    def sched_switch_per_cpu(self, cpu_id, ts, next_tid, event):
        """Compute per-cpu usage"""
        if cpu_id in self.cpus:
            c = self.cpus[cpu_id]
            if c.start_task_ns != 0:
                c.cpu_ns += ts - c.start_task_ns
            # exclude swapper process
            if next_tid != 0:
                c.start_task_ns = ts
                c.current_tid = next_tid
            else:
                c.start_task_ns = 0
                c.current_tid = -1
        else:
            c = CPU()
            c.cpu_id = cpu_id
            c.current_tid = next_tid
            # when we schedule a real task (not swapper)
            c.start_task_ns = ts
            # first activity on the CPU
            self.cpus[cpu_id] = c
            self.cpus[cpu_id].total_per_cpu_pc_list = []
        for context in event.keys():
            if context.startswith("perf_"):
                c.perf[context] = event[context]

    def sched_switch_per_tid(self, ts, prev_tid, next_tid, next_comm, cpu_id, event, ret):
        """Compute per-tid usage"""
        # per-tid usage
        if prev_tid in self.tids:
            p = self.tids[prev_tid]
            p.cpu_ns += (ts - p.last_sched)
            c = self.cpus[cpu_id]
            for context in event.keys():
                if context.startswith("perf_"):
                    if not context in c.perf.keys():
                        c.perf[context] = event[context]
                    if not context in p.perf.keys():
                        p.perf[context] = event[context]
                    else:
                        # add the difference between the last known value
                        # for this counter on the current CPU
                        diff = event[context] - c.perf[context]
                        p.perf[context] += diff
                        if diff > 0:
                            ret[context] = diff

        # exclude swapper process
        if next_tid == 0:
            return

        if not next_tid in self.tids:
            p = Process()
            p.tid = next_tid
            p.comm = next_comm
            self.tids[next_tid] = p
        else:
            p = self.tids[next_tid]
            p.comm = next_comm
        p.last_sched = ts
        return ret

    def switch(self, event):
        """Handle sched_switch event, returns a dict of changed values"""
        prev_tid = event["prev_tid"]
        next_comm = event["next_comm"]
        next_tid = event["next_tid"]
        cpu_id = event["cpu_id"]
        ret = {}

        self.sched_switch_per_tid(event.timestamp, prev_tid, next_tid, next_comm,
                cpu_id, event, ret)
        # because of perf events check, we need to do the CPU analysis after
        # the per-tid analysis
        self.sched_switch_per_cpu(cpu_id, event.timestamp, next_tid, event)
        return ret

    def migrate_task(self, event):
        tid = event["tid"]
        if not tid in self.tids:
            p = Process()
            p.tid = tid
            p.comm = event["comm"]
            self.tids[tid] = p
        else:
            p = self.tids[tid]
        p.migrate_count += 1

    def fix_process(self, name, tid, pid):
        if not tid in self.tids:
            p = Process()
            p.tid = tid
            self.tids[tid] = p
        else:
            p = self.tids[tid]
        p.pid = pid
        p.comm = name

        if not pid in self.tids:
            p = Process()
            p.tid = pid
            self.tids[pid] = p
        else:
            p = self.tids[pid]
        p.pid = pid
        p.comm = name

    def dup_fd(self, fd):
        f = FD()
        f.filename = fd.filename
        f.fd = fd.fd
        f.fdtype = fd.fdtype
        return f

    def process_fork(self, event):
        child_tid = event["child_tid"]
        child_pid = event["child_pid"]
        child_comm = event["child_comm"]
        parent_pid = event["parent_pid"]
        parent_tid = event["parent_pid"]
        parent_comm = event["parent_comm"]
        f = Process()
        f.tid = child_tid
        f.pid = child_pid
        f.comm = child_comm

        # make sure the parent exists
        self.fix_process(parent_comm, parent_tid, parent_pid)
        p = self.tids[parent_pid]
        for fd in p.fds.keys():
            f.fds[fd] = self.dup_fd(p.fds[fd])
            f.fds[fd].parent = parent_pid

        self.tids[child_tid] = f

    def process_exec(self, event):
        tid = event["tid"]
        if not tid in self.tids:
            p = Process()
            p.tid = tid
            self.tids[tid] = p
        else:
            p = self.tids[tid]
        if "procname" in event.keys():
            p.comm = event["procname"]
        toremove = []
        for fd in p.fds.keys():
            if p.fds[fd].cloexec == 1:
                toremove.append(fd)
        for fd in toremove:
            p.fds.pop(fd, None)
