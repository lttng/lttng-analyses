#!/usr/bin/env python3
#
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

from .analysis import Analysis


class Memtop(Analysis):
    def __init__(self, state):
        notification_cbs = {
            'tid_page_alloc': self._process_tid_page_alloc,
            'tid_page_free': self._process_tid_page_free
        }

        self._state = state
        self._state.register_notification_cbs(notification_cbs)
        self.tids = {}

    def process_event(self, ev):
        pass

    def reset(self):
        for tid in self.tids:
            self.tids[tid].reset()

    def _process_tid_page_alloc(self, **kwargs):
        proc = kwargs['proc']
        tid = proc.tid
        if tid not in self.tids:
            self.tids[tid] = ProcessMemStats.new_from_process(proc)

        self.tids[tid].allocated_pages += 1

    def _process_tid_page_free(self, **kwargs):
        proc = kwargs['proc']
        tid = proc.tid
        if tid not in self.tids:
            self.tids[tid] = ProcessMemStats.new_from_process(proc)

        self.tids[tid].freed_pages += 1


class ProcessMemStats():
    def __init__(self, pid, tid, comm):
        self.pid = pid
        self.tid = tid
        self.comm = comm
        self.allocated_pages = 0
        self.freed_pages = 0

    @classmethod
    def new_from_process(cls, proc):
        return cls(proc.pid, proc.tid, proc.comm)

    def reset(self):
        self.allocated_pages = 0
        self.freed_pages = 0
