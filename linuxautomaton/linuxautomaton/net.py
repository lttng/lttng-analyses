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
