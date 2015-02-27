#!/usr/bin/env python3
#
# The MIT License (MIT)
#
# Copyright (C) 2015 - Julien Desfossez <jdesfossez@efficios.com>
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

from linuxautomaton import sp


class MemStateProvider(sp.StateProvider):
    def __init__(self, state):
        self.state = state
        cbs = {
            'mm_page_alloc': self._process_mm_page_alloc,
            'mm_page_free': self._process_mm_page_free
        }
        self._register_cbs(cbs)

    def process_event(self, ev):
        self._process_event_cb(ev)

    def _get_current_proc(self, event):
        cpu_id = event["cpu_id"]
        if cpu_id not in self.state.cpus:
            return None

        cpu = self.state.cpus[cpu_id]
        if cpu.current_tid is None:
            return None

        return self.state.tids[cpu.current_tid]

    def _process_mm_page_alloc(self, event):
        self.state.mm.page_count += 1

        # Increment the number of pages allocated during the execution
        # of all currently pending syscalls
        for process in self.state.tids.values():
            if not process.current_syscall:
                continue

            if "pages_allocated" not in process.current_syscall:
                process.current_syscall["pages_allocated"] = 1
            else:
                process.current_syscall["pages_allocated"] += 1

        current_process = self._get_current_proc(event)
        if current_process is None:
            return

        current_process.allocated_pages += 1

    def _process_mm_page_free(self, event):
        if self.state.mm.page_count == 0:
            return

        self.state.mm.page_count -= 1

        # Track the number of pages freed by the currently executing process
        current_process = self._get_current_proc(event)
        if current_process is None:
            return

        current_process.freed_pages += 1
