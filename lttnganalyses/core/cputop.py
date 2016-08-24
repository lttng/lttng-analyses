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

from . import stats
from .analysis import Analysis, PeriodData


class _PeriodData(PeriodData):
    def __init__(self):
        self.period_begin_ts = None
        self.cpus = {}
        self.tids = {}


class Cputop(Analysis):
    def __init__(self, state, conf):
        notification_cbs = {
            'sched_migrate_task': self._process_sched_migrate_task,
            'sched_switch_per_cpu': self._process_sched_switch_per_cpu,
            'sched_switch_per_tid': self._process_sched_switch_per_tid,
            'prio_changed': self._process_prio_changed,
        }

        super().__init__(state, conf, notification_cbs)

    def _create_period_data(self):
        return _PeriodData()

    def _begin_period_cb(self, period_data):
        period = period_data.period
        period_data.period_begin_ts = period.begin_evt.timestamp

    def _end_period_cb(self, period_data, completed, begin_captures,
                       end_captures):
        self._compute_stats(period_data)

    def _compute_stats(self, period_data):
        """Compute usage stats relative to a certain time range

        For each CPU and process tracked by the analysis, we set its
        usage_percent attribute, which represents the percentage of
        usage time for the given CPU or process relative to the full
        duration of the time range. Do note that we need to know the
        timestamps and not just the duration, because if a CPU or a
        process is currently busy, we use the end timestamp to add
        the partial results of the currently running task to the usage
        stats.
        """
        duration = self.last_event_ts - period_data.period.begin_evt.timestamp

        for cpu_id in period_data.cpus:
            cpu = period_data.cpus[cpu_id]
            if cpu.current_task_start_ts is not None:
                cpu.total_usage_time += self.last_event_ts - \
                    cpu.current_task_start_ts

            cpu.compute_stats(duration)

        for tid in period_data.tids:
            proc = period_data.tids[tid]
            if proc.last_sched_ts is not None:
                proc.total_cpu_time += self.last_event_ts - \
                    proc.last_sched_ts

            proc.compute_stats(duration)

    def _process_sched_switch_per_cpu(self, period_data, **kwargs):
        timestamp = kwargs['timestamp']
        cpu_id = kwargs['cpu_id']
        wakee_proc = kwargs['wakee_proc']

        if not self._filter_cpu(cpu_id):
            return

        if cpu_id not in period_data.cpus:
            period_data.cpus[cpu_id] = CpuUsageStats(cpu_id)
            period_data.cpus[cpu_id].current_task_start_ts = \
                period_data.period_begin_ts

        cpu = period_data.cpus[cpu_id]
        if cpu.current_task_start_ts is not None:
            cpu.total_usage_time += timestamp - cpu.current_task_start_ts

        if not self._filter_process(wakee_proc):
            cpu.current_task_start_ts = None
        else:
            cpu.current_task_start_ts = timestamp

    def _process_sched_switch_per_tid(self, period_data, **kwargs):
        cpu_id = kwargs['cpu_id']
        wakee_proc = kwargs['wakee_proc']
        timestamp = kwargs['timestamp']
        prev_tid = kwargs['prev_tid']
        next_tid = kwargs['next_tid']
        next_comm = kwargs['next_comm']

        if not self._filter_cpu(cpu_id):
            return

        if prev_tid not in period_data.tids:
            period_data.tids[prev_tid] = ProcessCpuStats(
                None, next_tid, next_comm)
            prev_proc = period_data.tids[prev_tid]
            # Set the last_sched_ts to the beginning of the period
            # since we missed the entry event.
            prev_proc.last_sched_ts = period_data.period_begin_ts

        prev_proc = period_data.tids[prev_tid]
        if prev_proc.last_sched_ts is not None:
            prev_proc.total_cpu_time += timestamp - prev_proc.last_sched_ts
            prev_proc.last_sched_ts = None

        # Only filter on wakee_proc after finalizing the prev_proc
        # accounting
        if not self._filter_process(wakee_proc):
            return

        if next_tid not in period_data.tids:
            period_data.tids[next_tid] = ProcessCpuStats(None,
                                                         next_tid, next_comm)
            period_data.tids[next_tid].update_prio(timestamp, wakee_proc.prio)

        next_proc = period_data.tids[next_tid]
        next_proc.last_sched_ts = timestamp

    def _process_sched_migrate_task(self, period_data, **kwargs):
        cpu_id = kwargs['cpu_id']
        proc = kwargs['proc']
        tid = proc.tid

        if not self._filter_process(proc):
            return
        if not self._filter_cpu(cpu_id):
            return

        if tid not in period_data.tids:
            period_data.tids[tid] = ProcessCpuStats.new_from_process(proc)

        period_data.tids[tid].migrate_count += 1

    def _process_prio_changed(self, period_data, **kwargs):
        timestamp = kwargs['timestamp']
        prio = kwargs['prio']
        tid = kwargs['tid']

        if tid not in period_data.tids:
            return

        period_data.tids[tid].update_prio(timestamp, prio)

    def _filter_process(self, proc):
        # Exclude swapper
        if proc.tid == 0:
            return False

        return super()._filter_process(proc)


class CpuUsageStats():
    def __init__(self, cpu_id):
        self.cpu_id = cpu_id
        # Usage time and start timestamp are in nanoseconds (ns)
        self.total_usage_time = 0
        self.current_task_start_ts = None
        self.usage_percent = None

    def compute_stats(self, duration):
        if duration != 0:
            self.usage_percent = self.total_usage_time * 100 / duration
        else:
            self.usage_percent = 0

    def reset(self):
        self.total_usage_time = 0
        self.usage_percent = None


class ProcessCpuStats(stats.Process):
    def __init__(self, pid, tid, comm):
        super().__init__(pid, tid, comm)

        # CPU Time and timestamp in nanoseconds (ns)
        self.total_cpu_time = 0
        self.last_sched_ts = None
        self.migrate_count = 0
        self.usage_percent = None

    def compute_stats(self, duration):
        if duration != 0:
            self.usage_percent = self.total_cpu_time * 100 / duration
        else:
            self.usage_percent = 0

    def reset(self):
        super().reset()
        self.total_cpu_time = 0
        self.migrate_count = 0
        self.usage_percent = None
