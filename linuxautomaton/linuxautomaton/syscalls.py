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

from linuxautomaton import sp


class SyscallsStateProvider(sp.StateProvider):
    def __init__(self, state):
        cbs = {
            'syscall_entry': self._process_syscall_entry,
            'syscall_exit': self._process_syscall_exit
        }

        self._state = state
        self._register_cbs(cbs)

    def process_event(self, ev):
        self._process_event_cb(ev)

    def _process_syscall_entry(self, event):
        name = event.name
        cpu_id = event['cpu_id']

        if cpu_id not in self._state.cpus:
            return

        cpu = self._state.cpus[cpu_id]
        if cpu.current_tid is None:
            return

        proc = self._state.tids[cpu.current_tid]
        proc.current_syscall['name'] = name
        proc.current_syscall['start'] = event.timestamp

    def _process_syscall_exit(self, event):
        cpu_id = event['cpu_id']
        if cpu_id not in self._state.cpus:
            return

        cpu = self._state.cpus[cpu_id]
        if cpu.current_tid is None:
            return

        proc = self._state.tids[cpu.current_tid]
        current_syscall = proc.current_syscall
        if not current_syscall:
            return

        current_syscall['duration'] = event.timestamp - \
                                      current_syscall['start']
        current_syscall['ret'] = event['ret']

        self._state.send_notification_cb('syscall_exit',
                                         proc=proc,
                                         event=event)

        self._state.tids[cpu.current_tid].current_syscall = {}
