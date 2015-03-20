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


class NetStateProvider(sp.StateProvider):
    def __init__(self, state):
        cbs = {
            'net_dev_xmit': self._process_net_dev_xmit,
            'netif_receive_skb': self._process_netif_receive_skb,
        }

        self._state = state
        self._register_cbs(cbs)

    def process_event(self, ev):
        self._process_event_cb(ev)

    def _process_net_dev_xmit(self, event):
        self._state.send_notification_cb('net_dev_xmit',
                                         iface_name=event['name'],
                                         sent_bytes=event['len'])

        cpu_id = event['cpu_id']
        if cpu_id not in self._state.cpus:
            return

        cpu = self._state.cpus[cpu_id]
        if cpu.current_tid is None:
            return

        current_syscall = self._state.tids[cpu.current_tid].current_syscall
        if not current_syscall:
            return

        if current_syscall['name'] in sv.SyscallConsts.WRITE_SYSCALLS and \
           current_syscall['fd'].fdtype == sv.FDType.unknown:
            current_syscall['fd'].fdtype = sv.FDType.maybe_net

    def _process_netif_receive_skb(self, event):
        self._state.send_notification_cb('netif_receive_skb',
                                         iface_name=event['name'],
                                         recv_bytes=event['len'])
