from LTTngAnalyzes.common import *

class BlockBio():
    def __init__(self, cpus, disks):
        self.cpus = cpus
        self.disks = disks

    def queue(self, event):
        dev = event["dev"]
        sector = event["sector"]
        nr_sector = event["nr_sector"]
        rq = {}
        rq["nr_sector"] = nr_sector
        rq["rq_time"] = event.timestamp

        d = get_disk(dev, self.disks)
        d.nr_requests += 1
        d.nr_sector += nr_sector
        d.pending_requests[sector] = rq

    def complete(self, event):
        dev = event["dev"]
        sector = event["sector"]
        nr_sector = event["nr_sector"]
        d = get_disk(dev, self.disks)

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
