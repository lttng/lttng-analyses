#!/usr/bin/env python3
#
# The MIT License (MIT)
#
# Copyright (C) 2015 - Julien Desfossez <jdesfosez@efficios.com>
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
        self.state = state
        self.ifaces = state.ifaces
        self.cpus = state.cpus
        self.tids = state.tids
        cbs = {
            'net_dev_xmit': self._process_net_dev_xmit,
            'netif_receive_skb': self._process_netif_receive_skb,
        }
        self._register_cbs(cbs)

    def process_event(self, ev):
        self._process_event_cb(ev)

    def get_dev(self, dev):
        if dev not in self.ifaces:
            d = sv.Iface()
            d.name = dev
            self.ifaces[dev] = d
        else:
            d = self.ifaces[dev]
        return d

    def _process_net_dev_xmit(self, event):
        dev = event["name"]
        sent_len = event["len"]
        cpu_id = event["cpu_id"]

        d = self.get_dev(dev)
        d.send_packets += 1
        d.send_bytes += sent_len

        if cpu_id not in self.cpus.keys():
            return
        c = self.cpus[cpu_id]
        if c.current_tid == -1:
            return
        t = self.tids[c.current_tid]
        if not t.current_syscall:
            return
        if t.current_syscall["name"] in sv.SyscallConsts.WRITE_SYSCALLS:
            if t.current_syscall["fd"].fdtype == sv.FDType.unknown:
                t.current_syscall["fd"].fdtype = sv.FDType.maybe_net

    def _process_netif_receive_skb(self, event):
        dev = event["name"]
        recv_len = event["len"]

        d = self.get_dev(dev)
        d.recv_packets += 1
        d.recv_bytes += recv_len
