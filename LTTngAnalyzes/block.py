from LTTngAnalyzes.common import Process, get_disk, IORequest


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
        # Note: since we don't know, we assume a sector is 512 bytes
        block_size = 512
        if nr_sector == 0:
            return

        rq = {}
        rq["nr_sector"] = nr_sector
        rq["rq_time"] = event.timestamp
        rq["iorequest"] = IORequest()
        rq["iorequest"].iotype = IORequest.IO_BLOCK
        rq["iorequest"].size = nr_sector * block_size

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
            if tid not in self.tids:
                p = Process()
                p.tid = tid
                self.tids[tid] = p
            else:
                p = self.tids[tid]
            if p.pid != -1 and p.tid != p.pid:
                p = self.tids[p.pid]
            rq["pid"] = p
            # even rwbs means read, odd means write
            if event["rwbs"] % 2 == 0:
                p.block_read += nr_sector * block_size
                rq["iorequest"].operation = IORequest.OP_READ
            else:
                p.block_write += nr_sector * block_size
                rq["iorequest"].operation = IORequest.OP_WRITE

    def complete(self, event):
        dev = event["dev"]
        sector = event["sector"]
        nr_sector = event["nr_sector"]
        if nr_sector == 0:
            return

        d = None
        for req in self.remap_requests:
            if req["dev"] == dev and req["sector"] == sector:
                d = get_disk(req["orig_dev"], self.disks)
                self.remap_requests.remove(req)

        if not d:
            d = get_disk(dev, self.disks)

        # ignore the completion of requests we didn't see the issue
        # because it would mess up the latency totals
        if sector not in d.pending_requests.keys():
            return

        rq = d.pending_requests[sector]
        if rq["nr_sector"] != nr_sector:
            return
        d.completed_requests += 1
        if rq["rq_time"] > event.timestamp:
            print("Weird request TS", event.timestamp)
        time_per_sector = (event.timestamp - rq["rq_time"]) / rq["nr_sector"]
        d.request_time += time_per_sector
        rq["iorequest"].duration = time_per_sector
        d.rq_list.append(rq["iorequest"])
        if "pid" in rq.keys():
            rq["pid"].iorequests.append(rq["iorequest"])
        del d.pending_requests[sector]

    def dump_orphan_requests(self):
        for req in self.remap_requests:
            print("Orphan : %d : %d %d" % (req["orig_dev"], req["dev"],
                                           req["sector"]))
