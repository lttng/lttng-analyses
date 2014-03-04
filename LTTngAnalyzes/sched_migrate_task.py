from LTTngAnalyzes.common import *

class SchedMigrateTask():
    def __init__(self, cpus, tids):
        self.cpus = cpus
        self.tids = tids

    def add(self, event):
        tid = event["tid"]
        if not tid in self.tids:
            p = Process()
            p.tid = tid
            p.comm = event["comm"]
            p.cpu_ns = 0
            p.migrate_count = 0
            p.syscalls = {}
            self.tids[tid] = p
        else:
            p = self.tids[tid]
        p.migrate_count += 1
