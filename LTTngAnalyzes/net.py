from LTTngAnalyzes.common import Iface, FDType, SyscallConsts


class Net():
    def __init__(self, ifaces, cpus, tids):
        self.ifaces = ifaces
        self.cpus = cpus
        self.tids = tids

    def get_dev(self, dev):
        if dev not in self.ifaces:
            d = Iface()
            d.name = dev
            self.ifaces[dev] = d
        else:
            d = self.ifaces[dev]
        return d

    def send(self, event):
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
        if t.current_syscall["name"] in SyscallConsts.WRITE_SYSCALLS:
            if t.current_syscall["fd"].fdtype == FDType.unknown:
                t.current_syscall["fd"].fdtype = FDType.maybe_net

    def recv(self, event):
        dev = event["name"]
        recv_len = event["len"]

        d = self.get_dev(dev)
        d.recv_packets += 1
        d.recv_bytes += recv_len
