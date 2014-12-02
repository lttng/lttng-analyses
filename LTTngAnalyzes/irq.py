from LTTngAnalyzes.common import IRQ


class Interrupt():
    def __init__(self, irq, cpus, tids):
        self.irq = irq
        self.cpus = cpus
        self.tids = tids
        self.irq["hard_count"] = 0
        self.irq["soft_count"] = 0
        self.irq["hard-per-cpu"] = {}
        self.irq["soft-per-cpu"] = {}
        self.irq["raise-per-cpu"] = {}
        self.irq["names"] = {}
        self.irq["hard-irqs"] = {}
        self.irq["soft-irqs"] = {}
        self.irq["raise-latency"] = {}

#    def get_current_proc(self, event):
#        cpu_id = event["cpu_id"]
#        if cpu_id not in self.cpus:
#            return None
#        c = self.cpus[cpu_id]
#        if c.current_tid == -1:
#            return None
#        return self.tids[c.current_tid]

    def entry(self, event, irqclass, idfield):
        cpu_id = event["cpu_id"]
        i = IRQ()
        i.irqclass = irqclass
        i.start_ts = event.timestamp
        i.cpu_id = cpu_id
        i.nr = event[idfield]
        return i

    def hard_entry(self, event):
        cpu_id = event["cpu_id"]
        self.irq["names"][event["irq"]] = event["name"]
        self.irq["hard_count"] += 1
        i = self.entry(event, IRQ.HARD_IRQ, "irq")
        self.irq["hard-per-cpu"][cpu_id] = i

    def soft_entry(self, event):
        cpu_id = event["cpu_id"]
        self.irq["soft_count"] += 1
        i = self.entry(event, IRQ.SOFT_IRQ, "vec")
        self.irq["soft-per-cpu"][cpu_id] = i
        if cpu_id in self.irq["raise-per-cpu"].keys() and \
                self.irq["raise-per-cpu"][cpu_id] is not None and \
                self.irq["raise-per-cpu"][cpu_id][1] == event["vec"]:
                    i.raise_ts = self.irq["raise-per-cpu"][cpu_id][0]
                    self.irq["raise-per-cpu"][cpu_id] = None

    def exit(self, event, idfield, per_cpu_key, global_key):
        cpu_id = event["cpu_id"]
        if cpu_id not in self.irq[per_cpu_key].keys() or \
                self.irq[per_cpu_key][cpu_id] is None:
                    return
        i = self.irq[per_cpu_key][cpu_id]
        if i.nr != event[idfield]:
            self.irq[per_cpu_key][cpu_id] = None
            return
        i.stop_ts = event.timestamp
        if not i.nr in self.irq[global_key].keys():
            self.irq[global_key][i.nr] = []
        self.irq[global_key][i.nr].append(i)
        return i

    def hard_exit(self, event):
        i = self.exit(event, "irq", "hard-per-cpu", "hard-irqs")
        i.ret = event["ret"]

    def soft_exit(self, event):
        self.exit(event, "vec", "soft-per-cpu", "soft-irqs")

    def soft_raise(self, event):
        cpu_id = event["cpu_id"]
        self.irq["raise-per-cpu"][cpu_id] = ((event.timestamp, event["vec"]))
