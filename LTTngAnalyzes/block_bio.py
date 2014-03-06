from LTTngAnalyzes.common import *

class BlockBio():
    def __init__(self, cpus, disks):
        self.cpus = cpus
        self.disks = disks

    def get_dev(self, dev):
        if not dev in self.disks:
            d = Disk()
            d.nr_sector = 0
            d.nr_requests = 0
            d.completed_requests = 0
            d.request_time = 0
            d.pending_requests = {}
            self.disks[dev] = d
        else:
            d = self.disks[dev]
        return d

    def queue(self, event):
        dev = event["dev"]
        sector = event["sector"]
        nr_sector = event["nr_sector"]
        rq = {}
        rq["nr_sector"] = nr_sector
        rq["rq_time"] = event.timestamp

        d = self.get_dev(dev)
        d.nr_requests += 1
        d.nr_sector += nr_sector
        d.pending_requests[sector] = rq

    def complete(self, event):
        dev = event["dev"]
        sector = event["sector"]
        nr_sector = event["nr_sector"]
        d = self.get_dev(dev)

        if not sector in d.pending_requests.keys():
            return
        rq = d.pending_requests[sector]
        if rq["nr_sector"] != nr_sector:
            return
        d.completed_requests += 1
        # yes it happens
        if rq["nr_sector"] == 0:
            return
        if rq["rq_time"] > event.timestamp:
            print("Weird request TS")
        time_per_sector = (event.timestamp - rq["rq_time"]) / rq["nr_sector"]
        d.request_time += time_per_sector
