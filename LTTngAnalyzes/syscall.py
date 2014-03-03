from LTTngAnalyzes.common import *

class Syscall():
    def __init__(self, cpus, tids):
        self.cpus = cpus
        self.tids = tids

    def entry(self, event):
        name = event.name
        cpu_id = event["cpu_id"]
        if not name in self.syscalls:
            s = Syscall()
            s.name = name
            s.count = 0
        else:
            s = self.syscalls[name]
        s.count += 1

    def exit(self, event):
        cpu_id = event["cpu_id"]
        pass
