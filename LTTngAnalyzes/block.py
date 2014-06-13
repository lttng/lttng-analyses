from LTTngAnalyzes.common import *

class Block():
    def __init__(self, cpus, disks, tids):
        self.cpus = cpus
        self.disks = disks
        self.tids = tids
        self.remap_requests = []

    def remap(self, event):
        dev = event["dev"]
        sector = event["sector"]
        old_dev = event["old_dev"]
        old_sector = event["old_sector"]

        for req in self.remap_requests:
            if req["dev"] == old_dev and req["sector"] == old_sector:
                req["dev"] = dev
                req["sector"] = sector
                return

        req = {}
        req["orig_dev"] = old_dev
        req["dev"] = dev
        req["sector"] = sector
        self.remap_requests.append(req)

    # For backmerge requests, just remove the request from the
    # remap_requests queue, because we rely later on the nr_sector
    # which has all the info we need.
    def backmerge(self, event):
        dev = event["dev"]
        sector = event["sector"]
        for req in self.remap_requests:
            if req["dev"] == dev and req["sector"] == sector:
                self.remap_requests.remove(req)

    def issue(self, event):
        dev = event["dev"]
        sector = event["sector"]
        nr_sector = event["nr_sector"]
        rq = {}
        rq["nr_sector"] = nr_sector
        rq["rq_time"] = event.timestamp

        d = None
        for req in self.remap_requests:
            if req["dev"] == dev and req["sector"] == sector:
                d = get_disk(req["orig_dev"], self.disks)
        if not d:
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
                p.block_write += event["nr_sector"] * 512

    def complete(self, event):
        dev = event["dev"]
        sector = event["sector"]
        nr_sector = event["nr_sector"]

        d = None
        for req in self.remap_requests:
            if req["dev"] == dev and req["sector"] == sector:
                d = get_disk(req["orig_dev"], self.disks)
                self.remap_requests.remove(req)

        if not d:
            d = get_disk(dev, self.disks)

        # ignore the completion of requests we didn't see the issue
        # because it would mess up the latency totals
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

    def dump_orphan_requests(self):
        for req in self.remap_requests:
            print("Orphan : %d : %d %d" % (req["orig_dev"], req["dev"], req["sector"]))
