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

from linuxautomaton import sp, sv


class IrqStateProvider(sp.StateProvider):
    def __init__(self, state):
        self.state = state
        cbs = {
            'irq_handler_entry': self._process_irq_handler_entry,
            'irq_handler_exit': self._process_irq_handler_exit,
            'softirq_raise': self._process_softirq_raise,
            'softirq_entry': self._process_softirq_entry,
            'softirq_exit': self._process_softirq_exit
        }
        self._register_cbs(cbs)

    def process_event(self, ev):
        self._process_event_cb(ev)

    def _get_cpu(self, cpu_id):
        if cpu_id not in self.state.cpus:
            self.state.cpus[cpu_id] = sv.CPU()

        return self.state.cpus[cpu_id]

    # Hard IRQs
    def _process_irq_handler_entry(self, event):
        cpu = self._get_cpu(event['cpu_id'])
        irq = sv.HardIRQ.new_from_irq_handler_entry(event)
        cpu.current_hard_irq = irq

        self.state._send_notification_cb('irq_handler_entry',
                                         id=irq.id,
                                         irq_name=event['name']
        )

    def _process_irq_handler_exit(self, event):
        cpu = self._get_cpu(event['cpu_id'])
        if cpu.current_hard_irq is None or \
           cpu.current_hard_irq.id != event['irq']:
            cpu.current_hard_irq = None
            return

        cpu.current_hard_irq.stop_ts = event.timestamp
        cpu.current_hard_irq.ret = event['ret']

        self.state._send_notification_cb('irq_handler_exit',
                                         hard_irq=cpu.current_hard_irq)
        cpu.current_hard_irq = None

    # SoftIRQs
    def _process_softirq_raise(self, event):
        cpu = self._get_cpu(event['cpu_id'])
        irq = sv.SoftIRQ.new_from_softirq_raise(event)
        cpu.current_softirqs.append(irq)

    def _process_softirq_entry(self, event):
        cpu = self._get_cpu(event['cpu_id'])
        if cpu.current_softirqs and \
           cpu.current_softirqs[0].id == event['vec']:
            cpu.current_softirqs[0].start_ts = event.timestamp
        else:
            irq = sv.SoftIRQ.new_from_softirq_entry(event)
            cpu.current_softirqs.append(irq)

    def _process_softirq_exit(self, event):
        cpu = self._get_cpu(event['cpu_id'])
        if not cpu.current_softirqs or\
           cpu.current_softirqs[0].id != event['vec']:
            return

        cpu.current_softirqs[0].stop_ts = event.timestamp
        self.state._send_notification_cb('softirq_exit',
                                         softirq=cpu.current_softirqs[0]
        )
        cpu.current_softirqs.pop(0)
