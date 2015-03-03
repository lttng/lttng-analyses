#!/usr/bin/env python3
#
# The MIT License (MIT)
#
# Copyright (C) 2015 - Julien Desfossez <jdesfossez@efficios.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from linuxautomaton import sp, sv, common


class BlockStateProvider(sp.StateProvider):
    def __init__(self, state):
        self.state = state
        self.cpus = state.cpus
        self.disks = state.disks
        self.tids = state.tids
        self.remap_requests = []
        cbs = {
            'block_rq_complete': self._process_block_rq_complete,
            'block_rq_issue': self._process_block_rq_issue,
            'block_bio_remap': self._process_block_bio_remap,
            'block_bio_backmerge': self._process_block_bio_backmerge,
        }
        self._register_cbs(cbs)

    def process_event(self, ev):
        self._process_event_cb(ev)

    def _process_block_bio_remap(self, event):
        dev = event['dev']
        sector = event['sector']
        old_dev = event['old_dev']
        old_sector = event['old_sector']

        for req in self.remap_requests:
            if req['dev'] == old_dev and req['sector'] == old_sector:
                req['dev'] = dev
                req['sector'] = sector
                return

        req = {}
        req['orig_dev'] = old_dev
        req['dev'] = dev
        req['sector'] = sector
        self.remap_requests.append(req)

    # For backmerge requests, just remove the request from the
    # remap_requests queue, because we rely later on the nr_sector
    # which has all the info we need.
    def _process_block_bio_backmerge(self, event):
        dev = event['dev']
        sector = event['sector']
        for req in self.remap_requests:
            if req['dev'] == dev and req['sector'] == sector:
                self.remap_requests.remove(req)

    def _process_block_rq_issue(self, event):
        dev = event['dev']
        sector = event['sector']
        nr_sector = event['nr_sector']
        # Note: since we don't know, we assume a sector is 512 bytes
        block_size = 512
        if nr_sector == 0:
            return

        rq = {}
        rq['nr_sector'] = nr_sector
        rq['rq_time'] = event.timestamp
        rq['iorequest'] = sv.IORequest()
        rq['iorequest'].iotype = sv.IORequest.IO_BLOCK
        rq['iorequest'].begin = event.timestamp
        rq['iorequest'].size = nr_sector * block_size

        d = None
        for req in self.remap_requests:
            if req['dev'] == dev and req['sector'] == sector:
                d = common.get_disk(req['orig_dev'], self.disks)
        if not d:
            d = common.get_disk(dev, self.disks)

        d.nr_requests += 1
        d.nr_sector += nr_sector
        d.pending_requests[sector] = rq

        if 'tid' in event.keys():
            tid = event['tid']
            if tid not in self.tids:
                p = sv.Process()
                p.tid = tid
                self.tids[tid] = p
            else:
                p = self.tids[tid]
            if p.pid is not None and p.tid != p.pid:
                p = self.tids[p.pid]
            rq['pid'] = p
            # even rwbs means read, odd means write
            if event['rwbs'] % 2 == 0:
                p.block_read += nr_sector * block_size
                rq['iorequest'].operation = sv.IORequest.OP_READ
            else:
                p.block_write += nr_sector * block_size
                rq['iorequest'].operation = sv.IORequest.OP_WRITE

    def _process_block_rq_complete(self, event):
        dev = event['dev']
        sector = event['sector']
        nr_sector = event['nr_sector']
        if nr_sector == 0:
            return

        d = None
        for req in self.remap_requests:
            if req['dev'] == dev and req['sector'] == sector:
                d = common.get_disk(req['orig_dev'], self.disks)
                self.remap_requests.remove(req)

        if not d:
            d = common.get_disk(dev, self.disks)

        # ignore the completion of requests we didn't see the issue
        # because it would mess up the latency totals
        if sector not in d.pending_requests.keys():
            return

        rq = d.pending_requests[sector]
        if rq['nr_sector'] != nr_sector:
            return
        d.completed_requests += 1
        time_per_sector = (event.timestamp - rq['rq_time']) / rq['nr_sector']
        d.request_time += time_per_sector
        rq['iorequest'].duration = time_per_sector
        rq['iorequest'].end = event.timestamp
        d.rq_list.append(rq['iorequest'])
        if 'pid' in rq.keys():
            rq['pid'].iorequests.append(rq['iorequest'])
        del d.pending_requests[sector]
