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
    _ANALYSIS_CLASS = memtop.Memtop

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
            if self._args.limit > 0 and count >= self._args.limit:
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
            if self._args.limit > 0 and count >= self._args.limit:
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
        Command._add_proc_filter_args(ap)


def run():
    memtopcmd = Memtop()
    memtopcmd.run()
