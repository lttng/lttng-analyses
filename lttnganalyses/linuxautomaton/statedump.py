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
        cbs = {
            'lttng_statedump_process_state':
            self._process_lttng_statedump_process_state,
            'lttng_statedump_file_descriptor':
            self._process_lttng_statedump_file_descriptor
        }

        super().__init__(state, cbs)

    def _process_lttng_statedump_process_state(self, event):
        tid = event['tid']
        pid = event['pid']
        name = event['name']
        # prio is not in the payload for LTTng-modules < 2.8. Using
        # get() will set it to None if the key is not found
        prio = event.get('prio')

        if tid not in self._state.tids:
            self._state.tids[tid] = sv.Process(tid=tid)

        proc = self._state.tids[tid]
        # Even if the process got created earlier, some info might be
        # missing, add it now.
        proc.pid = pid
        proc.comm = name
        # However don't override the prio value if we already got the
        # information from sched_* events.
        if proc.prio is None:
            proc.prio = prio

        if pid != tid:
            # create the parent
            if pid not in self._state.tids:
                # FIXME: why is the parent's name set to that of the
                # child? does that make sense?

                # tid == pid for the parent process
                self._state.tids[pid] = sv.Process(tid=pid, pid=pid, comm=name)

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
            self._state.tids[pid] = sv.Process(tid=pid, pid=pid)

        proc = self._state.tids[pid]

        if fd not in proc.fds:
            proc.fds[fd] = sv.FD(fd, filename, sv.FDType.unknown, cloexec)
            self._state.send_notification_cb('create_fd',
                                             fd=fd,
                                             parent_proc=proc,
                                             timestamp=event.timestamp,
                                             cpu_id=event['cpu_id'])
        else:
            # just fix the filename
            proc.fds[fd].filename = filename
            self._state.send_notification_cb('update_fd',
                                             fd=fd,
                                             parent_proc=proc,
                                             timestamp=event.timestamp,
                                             cpu_id=event['cpu_id'])

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
