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
from ..core import memtop
from ..ascii_graph import Pyasciigraph
import operator


class Memtop(Command):
    _DESC = """The memtop command."""

    def __init__(self):
        super().__init__(self._add_arguments, enable_proc_filter_args=True)

    def _validate_transform_args(self):
        pass

    def run(self):
        # parse arguments first
        self._parse_args()
        # validate, transform and save specific arguments
        self._validate_transform_args()
        # open the trace
        self._open_trace()
        # create the appropriate analysis/analyses
        self._create_analysis()
        # run the analysis
        self._run_analysis(self._reset_total, self._refresh)
        # print results
        self._print_results(self.start_ns, self.trace_end_ts)
        # close the trace
        self._close_trace()

    def _create_analysis(self):
        self._analysis = memtop.Memtop(self.state)

    def _reset_total(self, start_ts):
        self._analysis.reset()

    def _refresh(self, begin, end):
        self._print_results(begin, end)
        self._reset_total(end)

    def _print_results(self, begin_ns, end_ns):
        self._print_date(begin_ns, end_ns)
        self._print_per_tid_alloc()
        self._print_per_tid_freed()
        self._print_total_alloc_freed()

    def _print_per_tid_alloc(self):
        graph = Pyasciigraph()
        values = []
        count = 0

        for tid in sorted(self._analysis.tids.values(),
                          key=operator.attrgetter('allocated_pages'),
                          reverse=True):
            if not self._filter_process(tid):
                continue

            values.append(('%s (%d)' % (tid.comm, tid.tid),
                          tid.allocated_pages))

            count += 1
            if self._arg_limit > 0 and count >= self._arg_limit:
                break

        for line in graph.graph('Per-TID Memory Allocations', values,
                                unit=' pages'):
            print(line)

    def _print_per_tid_freed(self):
        graph = Pyasciigraph()
        values = []
        count = 0

        for tid in sorted(self._analysis.tids.values(),
                          key=operator.attrgetter('freed_pages'),
                          reverse=True):
            if not self._filter_process(tid):
                continue

            values.append(('%s (%d)' % (tid.comm, tid.tid), tid.freed_pages))

            count += 1
            if self._arg_limit > 0 and count >= self._arg_limit:
                break

        for line in graph.graph('Per-TID Memory Deallocation', values,
                                unit=' pages'):
            print(line)

    def _print_total_alloc_freed(self):
        alloc = 0
        freed = 0

        for tid in self._analysis.tids.values():
            if not self._filter_process(tid):
                continue

            alloc += tid.allocated_pages
            freed += tid.freed_pages

        print('\nTotal memory usage:\n- %d pages allocated\n- %d pages freed' %
              (alloc, freed))

    def _add_arguments(self, ap):
        # specific argument
        pass


# entry point
def run():
    # create command
    memtopcmd = Memtop()

    # execute command
    memtopcmd.run()
