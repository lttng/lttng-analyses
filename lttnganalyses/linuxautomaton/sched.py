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

from . import sp, sv


class SchedStateProvider(sp.StateProvider):
    def __init__(self, state):
        cbs = {
            'sched_switch': self._process_sched_switch,
            'sched_migrate_task': self._process_sched_migrate_task,
            'sched_wakeup': self._process_sched_wakeup,
            'sched_wakeup_new': self._process_sched_wakeup,
            'sched_process_fork': self._process_sched_process_fork,
            'sched_process_exec': self._process_sched_process_exec,
        }

        self._state = state
        self._register_cbs(cbs)

    def process_event(self, ev):
        self._process_event_cb(ev)

    def _fix_process(self, tid, pid, comm):
        """Fix a process' pid and comm if it exists, create it otherwise"""
        if tid not in self._state.tids:
            proc = sv.Process(tid, pid, comm)
            self._state.tids[tid] = proc
        else:
            proc = self._state.tids[tid]
            proc.pid = pid
            proc.comm = comm

    def _sched_switch_per_cpu(self, cpu_id, next_tid):
        if cpu_id not in self._state.cpus:
            self._state.cpus[cpu_id] = sv.CPU(cpu_id)

        cpu = self._state.cpus[cpu_id]
        # exclude swapper process
        if next_tid == 0:
            cpu.current_tid = None
        else:
            cpu.current_tid = next_tid

    def _sched_switch_per_tid(self, next_tid, next_comm, prev_tid):
        if next_tid not in self._state.tids:
            if next_tid == 0:
                # special case for the swapper
                self._state.tids[next_tid] = sv.Process(tid=next_tid, pid=0)
            else:
                self._state.tids[next_tid] = sv.Process(tid=next_tid)

        next_proc = self._state.tids[next_tid]
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

        self._state.send_notification_cb('sched_switch_per_cpu',
                                         timestamp=timestamp,
                                         cpu_id=cpu_id,
                                         next_tid=next_tid)
        self._state.send_notification_cb('sched_switch_per_tid',
                                         timestamp=timestamp,
                                         prev_tid=prev_tid,
                                         next_tid=next_tid,
                                         next_comm=next_comm)

    def _process_sched_migrate_task(self, event):
        tid = event['tid']
        if tid not in self._state.tids:
            proc = sv.Process()
            proc.tid = tid
            proc.comm = event['comm']
            self._state.tids[tid] = proc
        else:
            proc = self._state.tids[tid]

        self._state.send_notification_cb('sched_migrate_task', proc=proc)

    def _process_sched_wakeup(self, event):
        target_cpu = event['target_cpu']
        tid = event['tid']

        if target_cpu not in self._state.cpus:
            self._state.cpus[target_cpu] = sv.CPU(target_cpu)

        if tid not in self._state.tids:
            proc = sv.Process()
            proc.tid = tid
            self._state.tids[tid] = proc

    def _process_sched_process_fork(self, event):
        child_tid = event['child_tid']
        child_pid = event['child_pid']
        child_comm = event['child_comm']
        parent_pid = event['parent_pid']
        parent_tid = event['parent_pid']
        parent_comm = event['parent_comm']

        child_proc = sv.Process(child_tid, child_pid, child_comm)

        self._fix_process(parent_tid, parent_pid, parent_comm)
        parent_proc = self._state.tids[parent_pid]

        for fd in parent_proc.fds:
            old_fd = parent_proc.fds[fd]
            child_proc.fds[fd] = sv.FD.new_from_fd(old_fd)
            # Note: the parent_proc key in the notification function
            # refers to the parent of the FD, which in this case is
            # the child_proc created by the fork
            self._state.send_notification_cb('create_fd',
                                             fd=fd,
                                             parent_proc=child_proc,
                                             timestamp=event.timestamp)

        self._state.tids[child_tid] = child_proc

    def _process_sched_process_exec(self, event):
        tid = event['tid']

        if tid not in self._state.tids:
            proc = sv.Process()
            proc.tid = tid
            self._state.tids[tid] = proc
        else:
            proc = self._state.tids[tid]

        # Use LTTng procname context if available
        if 'procname' in event:
            proc.comm = event['procname']

        toremove = []
        for fd in proc.fds:
            if proc.fds[fd].cloexec:
                toremove.append(fd)
        for fd in toremove:
            self._state.send_notification_cb('close_fd',
                                             fd=fd,
                                             parent_proc=proc,
                                             timestamp=event.timestamp)
            del proc.fds[fd]
