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

from .sched import SchedStateProvider
from .mem import MemStateProvider
from .irq import IrqStateProvider
from .syscalls import SyscallsStateProvider
from .io import IoStateProvider
from .statedump import StatedumpStateProvider
from .block import BlockStateProvider
from .net import NetStateProvider
from .sv import MemoryManagement


class State:
    def __init__(self):
        self.cpus = {}
        self.tids = {}
        self.disks = {}
        self.mm = MemoryManagement()
        self._notification_cbs = {}
        # State changes can be handled differently depending on
        # version of tracer used, so keep track of it.
        self._tracer_version = None

    def register_notification_cbs(self, cbs):
        for name in cbs:
            if name not in self._notification_cbs:
                self._notification_cbs[name] = []

            self._notification_cbs[name].append(cbs[name])

    def send_notification_cb(self, name, **kwargs):
        if name in self._notification_cbs:
            for cb in self._notification_cbs[name]:
                cb(**kwargs)


class Automaton:
    def __init__(self):
        self._state = State()
        self._state_providers = [
            SchedStateProvider(self._state),
            MemStateProvider(self._state),
            IrqStateProvider(self._state),
            SyscallsStateProvider(self._state),
            IoStateProvider(self._state),
            StatedumpStateProvider(self._state),
            BlockStateProvider(self._state),
            NetStateProvider(self._state)
        ]

    def process_event(self, ev):
        for sp in self._state_providers:
            sp.process_event(ev)

    @property
    def state(self):
        return self._state
