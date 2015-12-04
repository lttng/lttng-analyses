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

from . import sp, sv


class NetStateProvider(sp.StateProvider):
    def __init__(self, state):
        cbs = {
            'net_dev_xmit': self._process_net_dev_xmit,
            'netif_receive_skb': self._process_netif_receive_skb,
        }

        super().__init__(state, cbs)

    def _process_net_dev_xmit(self, event):
        self._state.send_notification_cb('net_dev_xmit',
                                         iface_name=event['name'],
                                         sent_bytes=event['len'],
                                         cpu_id=event['cpu_id'])

        cpu_id = event['cpu_id']
        if cpu_id not in self._state.cpus:
            return

        cpu = self._state.cpus[cpu_id]
        if cpu.current_tid is None:
            return

        proc = self._state.tids[cpu.current_tid]
        current_syscall = proc.current_syscall
        if current_syscall is None:
            return

        if proc.pid is not None and proc.pid != proc.tid:
            proc = self._state.tids[proc.pid]

        if current_syscall.name in sv.SyscallConsts.WRITE_SYSCALLS:
            # TODO: find a way to set fd_type on the write rq to allow
            # setting FD Type if FD hasn't yet been created
            fd = current_syscall.io_rq.fd
            if fd in proc.fds and proc.fds[fd].fd_type == sv.FDType.unknown:
                proc.fds[fd].fd_type = sv.FDType.maybe_net

    def _process_netif_receive_skb(self, event):
        self._state.send_notification_cb('netif_receive_skb',
                                         iface_name=event['name'],
                                         recv_bytes=event['len'],
                                         cpu_id=event['cpu_id'])
