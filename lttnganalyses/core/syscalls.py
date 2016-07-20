# The MIT License (MIT)
#
# Copyright (C) 2015 - Antoine Busque <abusque@efficios.com>
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
        self.tids = {}
        self.total_syscalls = 0


class SyscallsAnalysis(Analysis):
    def __init__(self, state, conf):
        notification_cbs = {
            'syscall_exit': self._process_syscall_exit
        }
        super().__init__(state, conf, notification_cbs)

    def _create_period_data(self):
        return _PeriodData()

    def _process_syscall_exit(self, period, **kwargs):
        cpu_id = kwargs['cpu_id']
        proc = kwargs['proc']
        tid = proc.tid
        current_syscall = proc.current_syscall
        name = current_syscall.name

        if not self._filter_process(proc):
            return
        if not self._filter_cpu(cpu_id):
            return

        if tid not in period.tids:
            period.tids[tid] = ProcessSyscallStats.new_from_process(proc)

        proc_stats = period.tids[tid]
        if name not in proc_stats.syscalls:
            proc_stats.syscalls[name] = SyscallStats(name)

        proc_stats.syscalls[name].update_stats(current_syscall)
        proc_stats.total_syscalls += 1
        period.total_syscalls += 1


class ProcessSyscallStats(stats.Process):
    def __init__(self, pid, tid, comm):
        super().__init__(pid, tid, comm)

        # indexed by syscall name
        self.syscalls = {}
        self.total_syscalls = 0

    def reset(self):
        pass


class SyscallStats():
    def __init__(self, name):
        self.name = name
        self.min_duration = None
        self.max_duration = None
        self.total_duration = 0
        self.syscalls_list = []

    @property
    def count(self):
        return len(self.syscalls_list)

    def update_stats(self, syscall):
        duration = syscall.duration

        if self.min_duration is None or self.min_duration > duration:
            self.min_duration = duration
        if self.max_duration is None or self.max_duration < duration:
            self.max_duration = duration

        self.total_duration += duration
        self.syscalls_list.append(syscall)
