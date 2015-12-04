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

from . import sp


class MemStateProvider(sp.StateProvider):
    def __init__(self, state):
        cbs = {
            'mm_page_alloc': self._process_mm_page_alloc,
            'kmem_mm_page_alloc': self._process_mm_page_alloc,
            'mm_page_free': self._process_mm_page_free,
            'kmem_mm_page_free': self._process_mm_page_free,
        }

        super().__init__(state, cbs)

    def _get_current_proc(self, event):
        cpu_id = event['cpu_id']
        if cpu_id not in self._state.cpus:
            return None

        cpu = self._state.cpus[cpu_id]
        if cpu.current_tid is None:
            return None

        return self._state.tids[cpu.current_tid]

    def _process_mm_page_alloc(self, event):
        self._state.mm.page_count += 1

        # Increment the number of pages allocated during the execution
        # of all currently syscall io requests
        for process in self._state.tids.values():
            if process.current_syscall is None:
                continue

            if process.current_syscall.io_rq:
                process.current_syscall.io_rq.pages_allocated += 1

        current_process = self._get_current_proc(event)
        if current_process is None:
            return

        self._state.send_notification_cb('tid_page_alloc',
                                         proc=current_process,
                                         cpu_id=event['cpu_id'])

    def _process_mm_page_free(self, event):
        if self._state.mm.page_count == 0:
            return

        self._state.mm.page_count -= 1

        current_process = self._get_current_proc(event)
        if current_process is None:
            return

        self._state.send_notification_cb('tid_page_free',
                                         proc=current_process,
                                         cpu_id=event['cpu_id'])
