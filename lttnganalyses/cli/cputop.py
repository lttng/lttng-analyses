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

from .command import Command
from ..core import cputop
from ..ascii_graph import Pyasciigraph
import operator


class Cputop(Command):
    _DESC = """The cputop command."""
    _ANALYSIS_CLASS = cputop.Cputop

    def _filter_process(self, proc):
        # Exclude swapper
        if proc.tid == 0:
            return False

        if self._args.proc_list and proc.comm not in self._args.proc_list:
            return False

        return True

    def _print_results(self, begin_ns, end_ns):
        self._print_date(begin_ns, end_ns)
        self._print_per_tid_usage()
        self._print_per_cpu_usage()
        self._print_total_cpu_usage()

    def _print_per_tid_usage(self):
        count = 0
        limit = self._args.limit
        graph = Pyasciigraph()
        values = []

        for tid in sorted(self._analysis.tids.values(),
                          key=operator.attrgetter('usage_percent'),
                          reverse=True):
            if not self._filter_process(tid):
                continue

            output_str = '%s (%d)' % (tid.comm, tid.tid)
            if tid.migrate_count > 0:
                output_str += ', %d migrations' % (tid.migrate_count)

            values.append((output_str, tid.usage_percent))

            count += 1
            if limit > 0 and count >= limit:
                break

        for line in graph.graph('Per-TID CPU Usage', values, unit=' %'):
            print(line)

    def _print_per_cpu_usage(self):
        graph = Pyasciigraph()
        values = []

        for cpu in sorted(self._analysis.cpus.values(),
                          key=operator.attrgetter('usage_percent'),
                          reverse=True):
            values.append(('CPU %d' % cpu.cpu_id, cpu.usage_percent))

        for line in graph.graph('Per-CPU Usage', values, unit=' %'):
            print(line)

    def _print_total_cpu_usage(self):
        cpu_count = len(self.state.cpus)
        usage_percent = 0

        if not cpu_count:
            return

        for cpu in sorted(self._analysis.cpus.values(),
                          key=operator.attrgetter('usage_percent'),
                          reverse=True):
            usage_percent += cpu.usage_percent

        # average per CPU
        usage_percent /= cpu_count
        print('\nTotal CPU Usage: %0.02f%%\n' % usage_percent)

    def _add_arguments(self, ap):
        Command._add_proc_filter_args(ap)


def run():
    cputopcmd = Cputop()
    cputopcmd.run()
