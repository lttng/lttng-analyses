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
            self.tids[tid] = p
        else:
            p = self.tids[tid]
        p.migrate_count += 1
