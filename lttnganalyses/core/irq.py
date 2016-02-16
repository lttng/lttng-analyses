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


class IrqAnalysis(Analysis):
    def __init__(self, state, conf):
        notification_cbs = {
            'irq_handler_entry': self._process_irq_handler_entry,
            'irq_handler_exit': self._process_irq_handler_exit,
            'softirq_exit': self._process_softirq_exit
        }

        super().__init__(state, conf)
        self._state.register_notification_cbs(notification_cbs)

        # Indexed by irq 'id' (irq or vec)
        self.hard_irq_stats = {}
        self.softirq_stats = {}
        # Log of individual interrupts
        self.irq_list = []

    def reset(self):
        self.irq_list = []
        for id in self.hard_irq_stats:
            self.hard_irq_stats[id].reset()
        for id in self.softirq_stats:
            self.softirq_stats[id].reset()

    def _process_irq_handler_entry(self, **kwargs):
        id = kwargs['id']
        name = kwargs['irq_name']
        if id not in self.hard_irq_stats:
            self.hard_irq_stats[id] = HardIrqStats(name)
        elif name not in self.hard_irq_stats[id].names:
            self.hard_irq_stats[id].names.append(name)

    def _process_irq_handler_exit(self, **kwargs):
        irq = kwargs['hard_irq']

        if not self._filter_cpu(irq.cpu_id):
            return

        if self._conf.min_duration is not None and \
           irq.duration < self._conf.min_duration:
            return
        if self._conf.max_duration is not None and \
           irq.duration > self._conf.max_duration:
            return

        self.irq_list.append(irq)
        if irq.id not in self.hard_irq_stats:
            self.hard_irq_stats[irq.id] = HardIrqStats()

        self.hard_irq_stats[irq.id].update_stats(irq)

    def _process_softirq_exit(self, **kwargs):
        irq = kwargs['softirq']

        if not self._filter_cpu(irq.cpu_id):
            return

        if self._conf.min_duration is not None and \
           irq.duration < self._conf.min_duration:
            return
        if self._conf.max_duration is not None and \
           irq.duration > self._conf.max_duration:
            return

        self.irq_list.append(irq)
        if irq.id not in self.softirq_stats:
            name = SoftIrqStats.names[irq.id]
            self.softirq_stats[irq.id] = SoftIrqStats(name)

        self.softirq_stats[irq.id].update_stats(irq)


class IrqStats():
    def __init__(self, name):
        self._name = name
        self.min_duration = None
        self.max_duration = None
        self.total_duration = 0
        self.irq_list = []

    @property
    def name(self):
        return self._name

    @property
    def count(self):
        return len(self.irq_list)

    def update_stats(self, irq):
        if self.min_duration is None or irq.duration < self.min_duration:
            self.min_duration = irq.duration

        if self.max_duration is None or irq.duration > self.max_duration:
            self.max_duration = irq.duration

        self.total_duration += irq.duration
        self.irq_list.append(irq)

    def reset(self):
        self.min_duration = None
        self.max_duration = None
        self.total_duration = 0
        self.irq_list = []


class HardIrqStats(IrqStats):
    NAMES_SEPARATOR = ', '

    def __init__(self, name='unknown'):
        super().__init__(name)
        self.names = [name]

    @property
    def name(self):
        return self.NAMES_SEPARATOR.join(self.names)


class SoftIrqStats(IrqStats):
    # from include/linux/interrupt.h
    names = {0: 'HI_SOFTIRQ',
             1: 'TIMER_SOFTIRQ',
             2: 'NET_TX_SOFTIRQ',
             3: 'NET_RX_SOFTIRQ',
             4: 'BLOCK_SOFTIRQ',
             5: 'BLOCK_IOPOLL_SOFTIRQ',
             6: 'TASKLET_SOFTIRQ',
             7: 'SCHED_SOFTIRQ',
             8: 'HRTIMER_SOFTIRQ',
             9: 'RCU_SOFTIRQ'}

    def __init__(self, name):
        super().__init__(name)
        self.min_raise_latency = None
        self.max_raise_latency = None
        self.total_raise_latency = 0
        self.raise_count = 0

    def update_stats(self, irq):
        super().update_stats(irq)

        if irq.raise_ts is None:
            return

        raise_latency = irq.begin_ts - irq.raise_ts
        if self.min_raise_latency is None or \
           raise_latency < self.min_raise_latency:
            self.min_raise_latency = raise_latency

        if self.max_raise_latency is None or \
           raise_latency > self.max_raise_latency:
            self.max_raise_latency = raise_latency

        self.total_raise_latency += raise_latency
        self.raise_count += 1

    def reset(self):
        super().reset()
        self.min_raise_latency = None
        self.max_raise_latency = None
        self.total_raise_latency = 0
        self.raise_count = 0
