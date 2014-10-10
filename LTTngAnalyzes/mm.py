from LTTngAnalyzes.common import *

class Mm():
    def __init__(self, cpus, tids, dirty_pages):
        self.mm = {}
        self.cpus = cpus
        self.tids = tids
        self.dirty_pages = dirty_pages
        self.mm["count"] = 0
        self.mm["dirty"] = 0

    def get_current_proc(self, event):
        cpu_id = event["cpu_id"]
        if not cpu_id in self.cpus:
            return None
        c = self.cpus[cpu_id]
        if c.current_tid == -1:
            return None
        return self.tids[c.current_tid]

    def page_alloc(self, event):
        self.mm["count"] += 1
        for p in self.tids.values():
            if len(p.current_syscall.keys()) == 0:
                continue
            if not "alloc" in p.current_syscall.keys():
                p.current_syscall["alloc"] = 1
            else:
                p.current_syscall["alloc"] += 1

    def page_free(self, event):
        if self.mm["count"] == 0:
            return
        self.mm["count"] -= 1

    def block_dirty_buffer(self, event):
        self.mm["dirty"] += 1
        c = self.cpus[event["cpu_id"]]
        if c.current_tid <= 0:
            return
        p = self.tids[c.current_tid]
        current_syscall = self.tids[c.current_tid].current_syscall
        if len(current_syscall.keys()) == 0:
            return
        if "fd" in current_syscall.keys():
            self.dirty_pages["pages"].append((p, current_syscall["name"],
                current_syscall["fd"].filename, current_syscall["fd"].fd))
        return

    def writeback_global_dirty_state(self, event):
        print("%s count : %d, count dirty : %d, nr_dirty : %d, nr_writeback : %d, nr_dirtied : %d, nr_written : %d" %
                (ns_to_hour_nsec(event.timestamp), self.mm["count"],
                    self.mm["dirty"], event["nr_dirty"],
                    event["nr_writeback"], event["nr_dirtied"],
                    event["nr_written"]))
        self.mm["dirty"] = 0
