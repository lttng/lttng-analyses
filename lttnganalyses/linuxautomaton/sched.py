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
from ..common import version_utils


class SchedStateProvider(sp.StateProvider):
    # The priority offset for sched_wak* events was fixed in
    # lttng-modules 2.7.1 upwards
    PRIO_OFFSET_FIX_VERSION = version_utils.Version(2, 7, 1)

    def __init__(self, state):
        cbs = {
            'sched_switch': self._process_sched_switch,
            'sched_migrate_task': self._process_sched_migrate_task,
            'sched_wakeup': self._process_sched_wakeup,
            'sched_wakeup_new': self._process_sched_wakeup,
            'sched_waking': self._process_sched_wakeup,
            'sched_process_fork': self._process_sched_process_fork,
            'sched_process_exec': self._process_sched_process_exec,
            'sched_pi_setprio': self._process_sched_pi_setprio,
        }

        super().__init__(state, cbs)

    def _sched_switch_per_cpu(self, cpu_id, next_tid):
        if cpu_id not in self._state.cpus:
            self._state.cpus[cpu_id] = sv.CPU(cpu_id)

        cpu = self._state.cpus[cpu_id]
        # exclude swapper process
        if next_tid == 0:
            cpu.current_tid = None
        else:
            cpu.current_tid = next_tid

    def _create_proc(self, tid):
        if tid not in self._state.tids:
            if tid == 0:
                # special case for the swapper
                self._state.tids[tid] = sv.Process(tid=tid, pid=0)
            else:
                self._state.tids[tid] = sv.Process(tid=tid)

    def _sched_switch_per_tid(self, next_tid, next_comm, prev_tid):
        # Instantiate processes if new
        self._create_proc(prev_tid)
        self._create_proc(next_tid)

        next_proc = self._state.tids[next_tid]
        next_proc.comm = next_comm
        next_proc.prev_tid = prev_tid

    def _check_prio_changed(self, timestamp, tid, prio):
        # Ignore swapper
        if tid == 0:
            return

        proc = self._state.tids[tid]

        if proc.prio != prio:
            proc.prio = prio
            self._state.send_notification_cb(
                'prio_changed', timestamp=timestamp, tid=tid, prio=prio)

    def _process_sched_switch(self, event):
        timestamp = event.timestamp
        cpu_id = event['cpu_id']
        next_tid = event['next_tid']
        next_comm = event['next_comm']
        next_prio = event['next_prio']
        prev_tid = event['prev_tid']
        prev_prio = event['prev_prio']

        self._sched_switch_per_cpu(cpu_id, next_tid)
        self._sched_switch_per_tid(next_tid, next_comm, prev_tid)
        self._check_prio_changed(timestamp, prev_tid, prev_prio)
        self._check_prio_changed(timestamp, next_tid, next_prio)

        wakee_proc = self._state.tids[next_tid]
        waker_proc = None
        if wakee_proc.last_waker is not None:
            waker_proc = self._state.tids[wakee_proc.last_waker]

        cb_data = {
            'timestamp': timestamp,
            'cpu_id': cpu_id,
            'prev_tid': prev_tid,
            'next_tid': next_tid,
            'next_comm': next_comm,
            'wakee_proc': wakee_proc,
            'waker_proc': waker_proc,
        }

        self._state.send_notification_cb('sched_switch_per_cpu', **cb_data)
        self._state.send_notification_cb('sched_switch_per_tid', **cb_data)

        wakee_proc.last_wakeup = None
        wakee_proc.last_waker = None

    def _process_sched_migrate_task(self, event):
        tid = event['tid']
        prio = event['prio']

        if tid not in self._state.tids:
            proc = sv.Process()
            proc.tid = tid
            proc.comm = event['comm']
            self._state.tids[tid] = proc
        else:
            proc = self._state.tids[tid]

        self._state.send_notification_cb(
            'sched_migrate_task', proc=proc, cpu_id=event['cpu_id'])
        self._check_prio_changed(event.timestamp, tid, prio)

    def _process_sched_wakeup(self, event):
        target_cpu = event['target_cpu']
        current_cpu = event['cpu_id']
        prio = event['prio']
        tid = event['tid']

        if self._state.tracer_version < self.PRIO_OFFSET_FIX_VERSION:
            prio -= 100

        if target_cpu not in self._state.cpus:
            self._state.cpus[target_cpu] = sv.CPU(target_cpu)

        if current_cpu not in self._state.cpus:
            self._state.cpus[current_cpu] = sv.CPU(current_cpu)

        # If the TID is already executing on a CPU, ignore this wakeup
        for cpu_id in self._state.cpus:
            cpu = self._state.cpus[cpu_id]
            if cpu.current_tid == tid:
                return

        if tid not in self._state.tids:
            proc = sv.Process()
            proc.tid = tid
            self._state.tids[tid] = proc

        self._check_prio_changed(event.timestamp, tid, prio)

        # A process can be woken up multiple times, only record
        # the first one
        if self._state.tids[tid].last_wakeup is None:
            self._state.tids[tid].last_wakeup = event.timestamp
            if self._state.cpus[current_cpu].current_tid is not None:
                self._state.tids[tid].last_waker = \
                    self._state.cpus[current_cpu].current_tid

    def _process_sched_process_fork(self, event):
        child_tid = event['child_tid']
        child_pid = event['child_pid']
        child_comm = event['child_comm']
        parent_pid = event['parent_pid']
        parent_tid = event['parent_pid']
        parent_comm = event['parent_comm']

        if parent_tid not in self._state.tids:
            self._state.tids[parent_tid] = sv.Process(
                parent_tid, parent_pid, parent_comm)
        else:
            self._state.tids[parent_tid].pid = parent_pid
            self._state.tids[parent_tid].comm = parent_comm

        parent_proc = self._state.tids[parent_pid]
        child_proc = sv.Process(child_tid, child_pid, child_comm)

        for fd in parent_proc.fds:
            old_fd = parent_proc.fds[fd]
            child_proc.fds[fd] = sv.FD.new_from_fd(old_fd)
            # Note: the parent_proc key in the notification function
            # refers to the parent of the FD, which in this case is
            # the child_proc created by the fork
            self._state.send_notification_cb(
                'create_fd', fd=fd, parent_proc=child_proc,
                timestamp=event.timestamp, cpu_id=event['cpu_id'])

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
            self._state.send_notification_cb(
                'close_fd', fd=fd, parent_proc=proc,
                timestamp=event.timestamp, cpu_id=event['cpu_id'])
            del proc.fds[fd]

    def _process_sched_pi_setprio(self, event):
        timestamp = event.timestamp
        newprio = event['newprio']
        tid = event['tid']

        self._check_prio_changed(timestamp, tid, newprio)
