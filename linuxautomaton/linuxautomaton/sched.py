#!/usr/bin/env python3
#
# The MIT License (MIT)
#
# Copyright (C) 2015 - Julien Desfossez <jdesfossez@efficios.com>
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

from linuxautomaton import sp, sv
from babeltrace import CTFScope


class SchedStateProvider(sp.StateProvider):
    def __init__(self, state):
        self.state = state
        cbs = {
            'sched_switch': self._process_sched_switch,
            'sched_migrate_task': self._process_sched_migrate_task,
            'sched_wakeup': self._process_sched_wakeup,
            'sched_wakeup_new': self._process_sched_wakeup,
            'sched_process_fork': self._process_sched_process_fork,
            'sched_process_exec': self._process_sched_process_exec,
        }
        self._register_cbs(cbs)

    def process_event(self, ev):
        self._process_event_cb(ev)

    def sched_switch_per_cpu(self, cpu_id, ts, next_tid, event):
        """Compute per-cpu usage"""
        if cpu_id in self.state.cpus:
            c = self.state.cpus[cpu_id]
            if c.start_task_ns != 0:
                c.cpu_ns += ts - c.start_task_ns
            # exclude swapper process
            if next_tid != 0:
                c.start_task_ns = ts
                c.current_tid = next_tid
            else:
                c.start_task_ns = 0
                c.current_tid = None
        else:
            self.add_cpu(cpu_id, ts, next_tid)
        for context in event.keys():
            if context.startswith('perf_'):
                c.perf[context] = event[context]

    def add_cpu(self, cpu_id, ts, next_tid):
        c = sv.CPU()
        c.cpu_id = cpu_id
        c.current_tid = next_tid
        # when we schedule a real task (not swapper)
        c.start_task_ns = ts
        # first activity on the sv.CPU
        self.state.cpus[cpu_id] = c
        self.state.cpus[cpu_id].total_per_cpu_pc_list = []

    def sched_switch_per_tid(self, ts, prev_tid, next_tid,
                             next_comm, cpu_id, event, ret):
        """Compute per-tid usage"""
        # if we don't know yet the sv.CPU, skip this
        if cpu_id not in self.state.cpus.keys():
            self.add_cpu(cpu_id, ts, next_tid)
        c = self.state.cpus[cpu_id]
        # per-tid usage
        if prev_tid in self.state.tids:
            p = self.state.tids[prev_tid]
            if p.last_sched is not None:
                p.cpu_ns += (ts - p.last_sched)
            # perf PMU counters checks
            for context in event.field_list_with_scope(
                    CTFScope.STREAM_EVENT_CONTEXT):
                if context.startswith('perf_'):
                    if context not in c.perf.keys():
                        c.perf[context] = event[context]
                    # add the difference between the last known value
                    # for this counter on the current sv.CPU
                    diff = event[context] - c.perf[context]
                    if context not in p.perf.keys():
                        p.perf[context] = diff
                    else:
                        p.perf[context] += diff
                    if diff > 0:
                        ret[context] = diff

        # exclude swapper process
        if next_tid == 0:
            return ret

        if next_tid not in self.state.tids:
            p = sv.Process()
            p.tid = next_tid
            p.comm = next_comm
            self.state.tids[next_tid] = p
        else:
            p = self.state.tids[next_tid]
            p.comm = next_comm
        p.last_sched = ts
        for q in c.wakeup_queue:
            if q['task'] == p:
                ret['sched_latency'] = ts - q['ts']
                ret['next_tid'] = next_tid
                c.wakeup_queue.remove(q)
        return ret

    def _process_sched_switch(self, event):
        """Handle sched_switch event, returns a dict of changed values"""
        prev_tid = event['prev_tid']
        next_comm = event['next_comm']
        next_tid = event['next_tid']
        cpu_id = event['cpu_id']
        ret = {}

        self.sched_switch_per_tid(event.timestamp, prev_tid,
                                  next_tid, next_comm,
                                  cpu_id, event, ret)
        # because of perf events check, we need to do the sv.CPU analysis after
        # the per-tid analysis
        self.sched_switch_per_cpu(cpu_id, event.timestamp, next_tid, event)
        if next_tid > 0:
            self.state.tids[next_tid].prev_tid = prev_tid

        return ret

    def _process_sched_migrate_task(self, event):
        tid = event['tid']
        if tid not in self.state.tids:
            p = sv.Process()
            p.tid = tid
            p.comm = event['comm']
            self.state.tids[tid] = p
        else:
            p = self.state.tids[tid]
        p.migrate_count += 1

    def _process_sched_wakeup(self, event):
        """Stores the sched_wakeup infos to compute scheduling latencies"""
        target_cpu = event['target_cpu']
        tid = event['tid']
        if target_cpu not in self.state.cpus.keys():
            c = sv.CPU()
            c.cpu_id = target_cpu
            self.state.cpus[target_cpu] = c
        else:
            c = self.state.cpus[target_cpu]

        if tid not in self.state.tids:
            p = sv.Process()
            p.tid = tid
            self.state.tids[tid] = p
        else:
            p = self.state.tids[tid]
        c.wakeup_queue.append({'ts': event.timestamp, 'task': p})

    def fix_process(self, name, tid, pid):
        if tid not in self.state.tids:
            p = sv.Process()
            p.tid = tid
            self.state.tids[tid] = p
        else:
            p = self.state.tids[tid]
        p.pid = pid
        p.comm = name

        if pid not in self.state.tids:
            p = sv.Process()
            p.tid = pid
            self.state.tids[pid] = p
        else:
            p = self.state.tids[pid]
        p.pid = pid
        p.comm = name

    def dup_fd(self, fd):
        f = sv.FD()
        f.filename = fd.filename
        f.fd = fd.fd
        f.fdtype = fd.fdtype
        return f

    def _process_sched_process_fork(self, event):
        child_tid = event['child_tid']
        child_pid = event['child_pid']
        child_comm = event['child_comm']
        parent_pid = event['parent_pid']
        parent_tid = event['parent_pid']
        parent_comm = event['parent_comm']
        f = sv.Process()
        f.tid = child_tid
        f.pid = child_pid
        f.comm = child_comm

        # make sure the parent exists
        self.fix_process(parent_comm, parent_tid, parent_pid)
        p = self.state.tids[parent_pid]
        for fd in p.fds.keys():
            f.fds[fd] = self.dup_fd(p.fds[fd])
            f.fds[fd].parent = parent_pid

        self.state.tids[child_tid] = f

    def _process_sched_process_exec(self, event):
        tid = event['tid']
        if tid not in self.state.tids:
            p = sv.Process()
            p.tid = tid
            self.state.tids[tid] = p
        else:
            p = self.state.tids[tid]
        if 'procname' in event.keys():
            p.comm = event['procname']
        toremove = []
        for fd in p.fds.keys():
            if p.fds[fd].cloexec == 1:
                toremove.append(fd)
        for fd in toremove:
            p.fds.pop(fd, None)
