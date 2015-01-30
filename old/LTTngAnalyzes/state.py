from LTTngAnalyzes.sched import Sched
from LTTngAnalyzes.net import Net
from LTTngAnalyzes.block import Block
from LTTngAnalyzes.statedump import Statedump
from LTTngAnalyzes.syscalls import Syscalls
from LTTngAnalyzes.mm import Mm
from LTTngAnalyzes.irq import Interrupt


class State():
    def __init__(self):
        self.cpus = {}
        self.tids = {}
        self.disks = {}
        self.syscalls = {}
        self.mm = {}
        self.ifaces = {}
        self.dirty_pages = {}
        self.interrupts = {}
        self.pending_syscalls = []

        self.sched = Sched(self.cpus, self.tids)
        self.syscall = Syscalls(self.cpus, self.tids, self.syscalls,
                                self.pending_syscalls)
        self.statedump = Statedump(self.tids, self.disks)
        self.mem = Mm(self.mm, self.cpus, self.tids, self.dirty_pages)
        self.block = Block(self.cpus, self.disks, self.tids)
        self.net = Net(self.ifaces, self.cpus, self.tids)
        self.irq = Interrupt(self.interrupts, self.cpus, self.tids)
