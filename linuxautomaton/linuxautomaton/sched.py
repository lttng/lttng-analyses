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

from linuxautomaton import sp, sv


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

    def _fix_process(self, tid, pid, comm):
        """Fix a process' pid and comm if it exists, create it otherwise"""
        if tid not in self.state.tids:
            proc = sv.Process(tid, pid, comm)
            self.state.tids[tid] = proc
        else:
            proc = self.state.tids[tid]
            proc.pid = pid
            proc.comm = comm

    def _sched_switch_per_cpu(self, cpu_id, next_tid):
        if cpu_id not in self.state.cpus:
            self.state.cpus[cpu_id] = sv.CPU(cpu_id)

        cpu = self.state.cpus[cpu_id]
        # exclude swapper process
        if next_tid == 0:
            cpu.current_tid = None
        else:
            cpu.current_tid = next_tid

    def _sched_switch_per_tid(self, next_tid, next_comm, prev_tid):
        if next_tid not in self.state.tids:
            if next_tid == 0:
                # special case for the swapper
                self.state.tids[next_tid] = sv.Process(tid=next_tid, pid=0)
            else:
                self.state.tids[next_tid] = sv.Process(tid=next_tid)

        next_proc = self.state.tids[next_tid]
        next_proc.comm = next_comm
        next_proc.prev_tid = prev_tid

    def _process_sched_switch(self, event):
        timestamp = event.timestamp
        cpu_id = event['cpu_id']
        next_tid = event['next_tid']
        next_comm = event['next_comm']
        prev_tid = event['prev_tid']

        self._sched_switch_per_cpu(cpu_id, next_tid)
        self._sched_switch_per_tid(next_tid, next_comm, prev_tid)

        self.state.send_notification_cb('sched_switch_per_cpu',
                                        timestamp=timestamp,
                                        cpu_id=cpu_id,
                                        next_tid=next_tid)
        self.state.send_notification_cb('sched_switch_per_tid',
                                        timestamp=timestamp,
                                        prev_tid=prev_tid,
                                        next_tid=next_tid,
                                        next_comm=next_comm)

    def _process_sched_migrate_task(self, event):
        tid = event['tid']
        if tid not in self.state.tids:
            proc = sv.Process()
            proc.tid = tid
            proc.comm = event['comm']
            self.state.tids[tid] = proc
        else:
            proc = self.state.tids[tid]

        self.state.send_notification_cb('sched_migrate_task', proc=proc)

    def _process_sched_wakeup(self, event):
        target_cpu = event['target_cpu']
        tid = event['tid']

        if target_cpu not in self.state.cpus:
            self.state.cpus[target_cpu] = sv.CPU(target_cpu)

        if tid not in self.state.tids:
            proc = sv.Process()
            proc.tid = tid
            self.state.tids[tid] = proc

    def _process_sched_process_fork(self, event):
        child_tid = event['child_tid']
        child_pid = event['child_pid']
        child_comm = event['child_comm']
        parent_pid = event['parent_pid']
        parent_tid = event['parent_pid']
        parent_comm = event['parent_comm']

        child_proc = sv.Process(child_tid, child_pid, child_comm)

        self._fix_process(parent_tid, parent_pid, parent_comm)
        parent_proc = self.state.tids[parent_pid]

        for fd in parent_proc.fds:
            old_fd = parent_proc.fds[fd]
            child_proc.fds[fd] = sv.FD.new_from_fd(old_fd)
            child_proc.fds[fd].parent = parent_pid

        self.state.tids[child_tid] = child_proc

    def _process_sched_process_exec(self, event):
        tid = event['tid']

        if tid not in self.state.tids:
            proc = sv.Process()
            proc.tid = tid
            self.state.tids[tid] = proc
        else:
            proc = self.state.tids[tid]

        # Use LTTng procname context if available
        if 'procname' in event:
            proc.comm = event['procname']

        toremove = []
        for fd in proc.fds:
            if proc.fds[fd].cloexec:
                toremove.append(fd)
        for fd in toremove:
            del proc.fds[fd]
