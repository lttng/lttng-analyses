#!/usr/bin/env python3
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the 'Software'), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

import sys
import argparse
import shutil
import time
from babeltrace import *
from LTTngAnalyzes.common import *
from LTTngAnalyzes.sched import *
from LTTngAnalyzes.statedump import *
from LTTngAnalyzes.syscalls import *
from analyzes import *
from ascii_graph import Pyasciigraph

class FDInfo():
    def __init__(self, traces, prefix, isOutputEnabled, pid, pname):
        self.prefix = prefix
        self.pid = pid
        self.pname = pname
        self.isOutputEnabled = isOutputEnabled
        self.traces = traces
        self.cpus = {}
        self.tids = {}
        self.disks = {}
        self.syscalls = {}
        self.open_syscalls = ['sys_open', 'sys_openat', 'sys_dup2',
                              'sys_accept', 'sys_socket', 'sys_fcntl']
        self.close_syscalls = ['sys_close']
        self.read_syscalls = ['sys_read', 'sys_recvmsg', 'sys_recvfrom',
                              'sys_splice', 'sys_readv', 'sys_sendfile64']
        self.write_syscalls = ['sys_write', 'sys_sendmsg' 'sys_sendto',
                               'sys_writev']

    def process_event(self, event, sched, syscall, statedump, started=1):
        if event.name == 'sched_switch':
            sched.switch(event)
        elif event.name.startswith('sys_'):
            self.handle_syscall_entry(event, syscall)
        elif event.name == 'exit_syscall':
            syscall.exit(event, started)
        elif event.name == 'sched_process_fork':
            sched.process_fork(event)
        elif event.name == 'lttng_statedump_process_state':
            statedump.process_state(event)
        elif event.name == 'lttng_statedump_file_descriptor':
            statedump.file_descriptor(event)
            if self.isOutputEnabled['dump']:
                self.output_dump(event)

    def handle_syscall_entry(self, event, syscall):
        if event.name in self.open_syscalls \
           and self.isOutputEnabled['open']:
            self.output_open(event)
        elif event.name in self.close_syscalls \
             and self.isOutputEnabled['close']:
            self.output_close(event)
        elif event.name in self.read_syscalls \
             and self.isOutputEnabled['read']:
            self.output_read(event)
        elif event.name in self.write_syscalls \
             and self.isOutputEnabled['write']:
            self.output_write(event)

        syscall.entry(event)

    def run(self, args):
        '''Process the trace'''
        self.current_sec = 0
        self.start_ns = 0
        self.end_ns = 0

        sched = Sched(self.cpus, self.tids)
        syscall = Syscalls(self.cpus, self.tids, self.syscalls)
        statedump = Statedump(self.tids, self.disks)

        for event in self.traces.events:
            self.process_event(event, sched, syscall, statedump)

    def output_dump(self, event):
        pid = event['pid']
        if(self.pid >= 0 and self.pid != pid):
            return

        comm = self.tids[pid].comm
        if self.pname is not None and self.pname != comm:
            return

        evt = event.name
        filename = event['filename']
        time = 'File opened before trace'

        if filename.startswith(self.prefix):
            print(pid, comm, evt, filename, time)
            
    def output_open(self, event):
        pid = self.cpus[event['cpu_id']].current_tid
        if(self.pid >= 0 and self.pid != pid):
            return

        comm = self.tids[pid].comm
        if self.pname is not None and self.pname != comm:
            return

        evt = event.name

        filename = self.compute_open_filename(event)
        if filename is None:
            return

        time = ns_to_hour_nsec(event.timestamp)
        
        if filename.startswith(self.prefix):
            print(pid, comm, evt, filename, time)

    def compute_open_filename(self, event):
        evt = event.name

        if evt in ['sys_open', 'sys_openat']:
            filename = event['filename']
        elif evt in ['sys_accept', 'sys_socket']:
            filename = 'socket'
        elif evt == 'sys_dup2':
            filename = self.tids[pid].fds[event['oldfd']].filename
        elif evt == 'sys_fcntl':
            if event['cmd'] != 0:
                return
            oldfd = event['fd']
            if oldfd in self.tids[pid].fds.keys():
                filename = proc.fds[oldfd].filename
            else:
                filename = ''

        return filename

    def output_close(self, event):
        pid = self.cpus[event['cpu_id']].current_tid
        if(self.pid >= 0 and self.pid != pid):
            return

        comm = self.tids[pid].comm
        if self.pname is not None and self.pname != comm:
            return

        evt = event.name
        fds = self.tids[pid].fds
        fd = event['fd']
        if not fd in fds.keys():
            return
        filename = fds[fd].filename
        time = ns_to_hour_nsec(event.timestamp)

        if filename.startswith(self.prefix):
            print(pid, comm, evt, filename, time)

    def output_read(self, event):
        pid = self.cpus[event['cpu_id']].current_tid
        if(self.pid >= 0 and self.pid != pid):
            return

        comm = self.tids[pid].comm
        if self.pname is not None and self.pname != comm:
            return

        evt = event.name
        fds = self.tids[pid].fds
        
        if evt == 'sys_splice':
            fd = event['fd_in']
        elif evt == 'sys_sendfile64':
            fd = event['in_fd']
        else:
            fd = event['fd']

        if not fd in fds.keys():
            return

        filename = fds[fd].filename
        time = ns_to_hour_nsec(event.timestamp)

        if filename.startswith(self.prefix):
            print(pid, comm, evt, filename, time)

    def output_write(self, event):
        pid = self.cpus[event['cpu_id']].current_tid
        if(self.pid >= 0 and self.pid != pid):
            return

        comm = self.tids[pid].comm
        if self.pname is not None and self.pname != comm:
            return

        evt = event.name
        fds = self.tids[pid].fds
        fd = event['fd']
        if not fd in fds.keys():
            return
        filename = fds[fd].filename
        time = ns_to_hour_nsec(event.timestamp)

        if filename.startswith(self.prefix):
            print(pid, comm, evt, filename, time)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='FD syscalls analysis')
    parser.add_argument('path', metavar='<path/to/trace>', help='Trace path')
    parser.add_argument('-p', '--prefix', type=str, default='',
                        help='Prefix in which to search')
    parser.add_argument('-t', '--type', type=str, default='all',
                        help='Types of events to display. Possible values:\
                        all, open, close, read, write dump')
    parser.add_argument('--pid', type=int, default='-1',
                        help='PID for which to display events')
    parser.add_argument('--pname', type=str, default=None,
                        help='Process name for which to display events')

    args = parser.parse_args()

    types = args.type.split(',')

    possibleTypes = ['open', 'close', 'read', 'write', 'dump']

    if 'all' in types:
        isOutputEnabled = { x: True for x in possibleTypes }
    else:
        isOutputEnabled = { x: False for x in possibleTypes }
        for type in types:
            if type in possibleTypes:
                isOutputEnabled[type] = True
            else:
                print('Invalid type:', type)
                parser.print_help()
                sys.exit(1)
    
    traces = TraceCollection()
    handle = traces.add_trace(args.path, 'ctf')
    if handle is None:
        sys.exit(1)

    c = FDInfo(traces, args.prefix, isOutputEnabled, args.pid, args.pname)

    c.run(args)

    traces.remove_trace(handle)
