from LTTngAnalyzes.common import *

class Net():
    def __init__(self, ifaces):
        self.ifaces = ifaces

    def get_dev(self, dev):
        if not dev in self.ifaces:
            d = Iface()
            d.name = dev
            self.ifaces[dev] = d
        else:
            d = self.ifaces[dev]
        return d

    def send(self, event):
        dev = event["name"]
        sent_len = event["len"]

        d = self.get_dev(dev)
        d.send_packets += 1
        d.send_bytes += sent_len

    def recv(self, event):
        dev = event["name"]
        recv_len = event["len"]

        d = self.get_dev(dev)
        d.recv_packets += 1
        d.recv_bytes += recv_len
