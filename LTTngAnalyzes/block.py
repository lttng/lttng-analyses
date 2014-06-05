from LTTngAnalyzes.common import *

class Block():
    def __init__(self, cpus, disks, tids):
        self.cpus = cpus
        self.disks = disks
        self.tids = tids

    def issue(self, event):
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

        if "tid" in event.keys():
            tid = event["tid"]
            if not tid in self.tids:
                p = Process()
                p.tid = tid
                self.tids[tid] = p
            else:
                p = self.tids[tid]
            if p.pid != -1 and p.tid != p.pid:
                p = self.tids[p.pid]
            # even rwbs means read, odd means write
            if event["rwbs"] % 2 == 0:
                # Note: since we don't know, we assume a sector is 512 bytes
                p.block_read += event["nr_sector"] * 512
            else:
                #print("LA : %d = %d" % (tid,  event["nr_sector"] * 512))
                p.block_write += event["nr_sector"] * 512

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
