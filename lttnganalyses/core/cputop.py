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

from .analysis import Analysis


class Cputop(Analysis):
    def __init__(self, state):
        notification_cbs = {
            'sched_migrate_task': self._process_sched_migrate_task,
            'sched_switch_per_cpu': self._process_sched_switch_per_cpu,
            'sched_switch_per_tid': self._process_sched_switch_per_tid
        }

        self._state = state
        self._state.register_notification_cbs(notification_cbs)
        self._ev_count = 0
        self.cpus = {}
        self.tids = {}

    def process_event(self, ev):
        self._ev_count += 1

    def reset(self, timestamp):
        for cpu_id in self.cpus:
            self.cpus[cpu_id].reset(timestamp)

        for tid in self.tids:
            self.tids[tid].reset(timestamp)

    def compute_stats(self, start_ts, end_ts):
        """Compute usage stats relative to a certain time range

        For each CPU and process tracked by the analysis, we set its
        usage_percent attribute, which represents the percentage of
        usage time for the given CPU or process relative to the full
        duration of the time range. Do note that we need to know the
        timestamps and not just the duration, because if a CPU or a
        process is currently busy, we use the end timestamp to add
        the partial results of the currently running task to the usage
        stats.

        Args:
        start_ts (int): start of time range (nanoseconds from unix
        epoch)
        end_ts (int): end of time range (nanoseconds from unix epoch)
        """
        duration = end_ts - start_ts

        for cpu_id in self.cpus:
            cpu = self.cpus[cpu_id]
            if cpu.current_task_start_ts is not None:
                cpu.total_usage_time += end_ts - cpu.current_task_start_ts

            cpu.compute_stats(duration)

        for tid in self.tids:
            proc = self.tids[tid]
            if proc.last_sched_ts is not None:
                proc.total_cpu_time += end_ts - proc.last_sched_ts

            proc.compute_stats(duration)

    def _process_sched_switch_per_cpu(self, **kwargs):
        timestamp = kwargs['timestamp']
        cpu_id = kwargs['cpu_id']
        next_tid = kwargs['next_tid']

        if cpu_id not in self.cpus:
            self.cpus[cpu_id] = CpuUsageStats(cpu_id)

        cpu = self.cpus[cpu_id]
        if cpu.current_task_start_ts is not None:
            cpu.total_usage_time += timestamp - cpu.current_task_start_ts

        if next_tid == 0:
            cpu.current_task_start_ts = None
        else:
            cpu.current_task_start_ts = timestamp

    def _process_sched_switch_per_tid(self, **kwargs):
        timestamp = kwargs['timestamp']
        prev_tid = kwargs['prev_tid']
        next_tid = kwargs['next_tid']
        next_comm = kwargs['next_comm']

        if prev_tid in self.tids:
            prev_proc = self.tids[prev_tid]
            if prev_proc.last_sched_ts is not None:
                prev_proc.total_cpu_time += timestamp - prev_proc.last_sched_ts
                prev_proc.last_sched_ts = None

        # Don't account for swapper process
        if next_tid == 0:
            return

        if next_tid not in self.tids:
            self.tids[next_tid] = ProcessCpuStats(next_tid, next_comm)

        next_proc = self.tids[next_tid]
        next_proc.last_sched_ts = timestamp

    def _process_sched_migrate_task(self, **kwargs):
        proc = kwargs['proc']
        tid = proc.tid
        if tid not in self.tids:
            self.tids[tid] = ProcessCpuStats.new_from_process(proc)

        self.tids[tid].migrate_count += 1

    @property
    def event_count(self):
        return self._ev_count


class CpuUsageStats():
    def __init__(self, cpu_id):
        self.cpu_id = cpu_id
        # Usage time and start timestamp are in nanoseconds (ns)
        self.total_usage_time = 0
        self.current_task_start_ts = None
        self.usage_percent = None

    def compute_stats(self, duration):
        self.usage_percent = self.total_usage_time * 100 / duration

    def reset(self, timestamp):
        self.total_usage_time = 0
        self.usage_percent = None
        if self.current_task_start_ts is not None:
            self.current_task_start_ts = timestamp


class ProcessCpuStats():
    def __init__(self, tid, comm):
        self.tid = tid
        self.comm = comm
        # CPU Time and timestamp in nanoseconds (ns)
        self.total_cpu_time = 0
        self.last_sched_ts = None
        self.migrate_count = 0
        self.usage_percent = None

    @classmethod
    def new_from_process(cls, proc):
        return cls(proc.tid, proc.comm)

    def compute_stats(self, duration):
        self.usage_percent = self.total_cpu_time * 100 / duration

    def reset(self, timestamp):
        self.total_cpu_time = 0
        self.migrate_count = 0
        self.usage_percent = None
        if self.last_sched_ts is not None:
            self.last_sched_ts = timestamp
