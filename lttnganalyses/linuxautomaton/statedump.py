#!/usr/bin/env python3
#
# The MIT License (MIT)
#
# Copyright (C) 2015 - Julien Desfossez <jdesfossez@efficios.com>
#               2015 - Antoine Busque <abusque@efficios.com>
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

from . import sp, sv, common


class StatedumpStateProvider(sp.StateProvider):
    def __init__(self, state):
        self._state = state
        cbs = {
            'lttng_statedump_process_state':
            self._process_lttng_statedump_process_state,
            'lttng_statedump_file_descriptor':
            self._process_lttng_statedump_file_descriptor
        }
        self._register_cbs(cbs)

    def process_event(self, ev):
        self._process_event_cb(ev)

    def _process_lttng_statedump_process_state(self, event):
        tid = event['tid']
        pid = event['pid']
        name = event['name']
        if tid not in self._state.tids:
            proc = sv.Process()
            proc.tid = tid
            self._state.tids[tid] = proc
        else:
            proc = self._state.tids[tid]
        # Even if the process got created earlier, some info might be
        # missing, add it now.
        proc.pid = pid
        proc.comm = name

        if pid != tid:
            # create the parent
            if pid not in self._state.tids:
                parent = sv.Process()
                parent.tid = pid
                parent.pid = pid
                parent.comm = name
                self._state.tids[pid] = parent
            else:
                parent = self._state.tids[pid]
            # If the thread had opened FDs, they need to be assigned
            # to the parent.
            StatedumpStateProvider._assign_fds_to_parent(proc, parent)
            self._state.send_notification_cb('create_parent_proc',
                                             proc=proc,
                                             parent_proc=parent)

    def _process_lttng_statedump_file_descriptor(self, event):
        pid = event['pid']
        fd = event['fd']
        filename = event['filename']
        cloexec = event['flags'] & common.O_CLOEXEC == common.O_CLOEXEC

        if pid not in self._state.tids:
            proc = sv.Process()
            proc.pid = pid
            proc.tid = pid
            self._state.tids[pid] = proc
        else:
            proc = self._state.tids[pid]

        if fd not in proc.fds:
            proc.fds[fd] = sv.FD(fd, filename, sv.FDType.unknown, cloexec)
            self._state.send_notification_cb('create_fd',
                                             fd=fd,
                                             parent_proc=proc,
                                             timestamp=event.timestamp)
        else:
            # just fix the filename
            proc.fds[fd].filename = filename

    @staticmethod
    def _assign_fds_to_parent(proc, parent):
        if proc.fds:
            toremove = []
            for fd in proc.fds:
                if fd not in parent.fds:
                    parent.fds[fd] = proc.fds[fd]
                else:
                    # best effort to fix the filename
                    if not parent.fds[fd].filename:
                        parent.fds[fd].filename = proc.fds[fd].filename
                toremove.append(fd)
            for fd in toremove:
                del proc.fds[fd]
