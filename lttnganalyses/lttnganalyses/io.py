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


class IoAnalysis(Analysis):
    def __init__(self, state):
        notification_cbs = {
            'net_dev_xmit': self._process_net_dev_xmit,
            'netif_receive_skb': self._process_netif_receive_skb
        }

        self._state = state
        self._state.register_notification_cbs(notification_cbs)
        self.ifaces = {}

    def process_event(self, ev):
        pass

    def reset(self):
        for iface in self.ifaces:
            iface.reset()

    def _process_net_dev_xmit(self, **kwargs):
        name = kwargs['iface_name']
        sent_bytes = kwargs['sent_bytes']

        if name not in self.ifaces:
            self.ifaces[name] = IfaceStats(name)

        self.ifaces[name].sent_packets += 1
        self.ifaces[name].sent_bytes += sent_bytes

    def _process_netif_receive_skb(self, **kwargs):
        name = kwargs['iface_name']
        recv_bytes = kwargs['recv_bytes']

        if name not in self.ifaces:
            self.ifaces[name] = IfaceStats(name)

        self.ifaces[name].recv_packets += 1
        self.ifaces[name].recv_bytes += recv_bytes


class IfaceStats():
    def __init__(self, name):
        self.name = name
        self.recv_bytes = 0
        self.recv_packets = 0
        self.sent_bytes = 0
        self.sent_packets = 0

    def reset(self):
        self.recv_bytes = 0
        self.recv_packets = 0
        self.sent_bytes = 0
        self.sent_packets = 0
