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
import errno
from babeltrace import *
from LTTngAnalyzes.common import *
from LTTngAnalyzes.sched import *
from LTTngAnalyzes.statedump import *
from LTTngAnalyzes.syscalls import *
from analyzes import *
from ascii_graph import Pyasciigraph

def parse_errname(errname):
    errname = errname.upper()

    try:
        errNumber = getattr(errno, errname)
    except AttributeError:
        print('Invalid errno name: ' + errname)
        sys.exit(1)

    return errNumber

class FDInfo():
    DUMP_FORMAT = '{0:18} {1:20} {2:<8} {3:20} {4:60}'
    SUCCESS_FORMAT = '{0:18} ({1:8f}) {2:20} {3:<8} {4:15} res={5:<3} {6:60}'
    FAILURE_FORMAT = '{0:18} ({1:8f}) {2:20} {3:<8} {4:15} res={5:<3} ({6}) \
    {7:60}'
    FAILURE_RED = '\033[31m'
    NORMAL_WHITE = '\033[37m'

    def __init__(self, traces, prefix, isOutputEnabled, pid, pname, failed,
                 duration_ms, isInteractive, noColor, errNumber):
        self.traces = traces
        self.prefix = prefix
        self.isOutputEnabled = isOutputEnabled
        self.pid = pid
        self.pname = pname
        self.failed = failed
        self.duration_ns = duration_ms * 1000000
        self.isInteractive = isInteractive
        self.noColor = noColor
        self.errNumber = errNumber
        self.cpus = {}
        self.tids = {}
        self.disks = {}
        self.syscalls = {}

    def process_event(self, event, sched, syscall, statedump, started=1):
        if event.name == 'sched_switch':
            sched.switch(event)
        elif event.name.startswith('sys_'):
            syscall.entry(event)
        elif event.name == 'exit_syscall':
            self.handle_syscall_exit(event, syscall)
        elif event.name == 'sched_process_fork':
            sched.process_fork(event)
        elif event.name == 'lttng_statedump_process_state':
            statedump.process_state(event)
        elif event.name == 'lttng_statedump_file_descriptor':
            statedump.file_descriptor(event)
            if self.isOutputEnabled['dump']:
                self.output_dump(event)

    def handle_syscall_exit(self, event, syscall, started = 1):
        cpu_id = event['cpu_id']
        if not cpu_id in self.cpus:
            return

        c = self.cpus[cpu_id]
        if c.current_tid == -1:
            return

        current_syscall = self.tids[c.current_tid].current_syscall
        if len(current_syscall.keys()) == 0:
            return

        name = current_syscall['name']
        if name in Syscalls.OPEN_SYSCALLS and self.isOutputEnabled['open'] or \
           name in Syscalls.CLOSE_SYSCALLS and self.isOutputEnabled['close'] or \
           name in Syscalls.READ_SYSCALLS and self.isOutputEnabled['read'] or \
           name in Syscalls.WRITE_SYSCALLS and self.isOutputEnabled['write']:
            self.output_fd_event(event, current_syscall)

        syscall.exit(event, started)

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
        # dump events can't fail, and don't have a duration, so ignore
        if self.failed or self.errNumber or self.duration_ns > 0:
            return

        pid = event['pid']
        if(self.pid >= 0 and self.pid != pid):
            return

        comm = self.tids[pid].comm
        if self.pname is not None and self.pname != comm:
            return

        evt = event.name
        filename = event['filename']
        time = ns_to_hour_nsec(event.timestamp)

        if filename.startswith(self.prefix):
            print(FDInfo.DUMP_FORMAT.format(time, comm, pid, evt, filename))

    def output_fd_event(self, exit_event, entry):
        ret = exit_event['ret']
        failed = ret < 0

        if self.failed and not failed:
            return

        if self.errNumber and ret != -errNumber:
            return

        pid = self.cpus[exit_event['cpu_id']].current_tid
        if(self.pid >= 0 and self.pid != pid):
            return

        comm = self.tids[pid].comm
        if self.pname is not None and self.pname != comm:
            return

        filename = entry['filename']
        if filename is None:
            return

        name = entry['name']

        endtime = ns_to_hour_nsec(exit_event.timestamp)
        duration_ns = (exit_event.timestamp - entry['start'])

        if self.duration_ns > 0 and duration_ns < self.duration_ns:
            return

        duration = duration_ns / 1000000000

        if self.isInteractive and failed and not self.noColor:
            sys.stdout.write(FDInfo.FAILURE_RED)

        if filename.startswith(self.prefix):
            if not failed:
                print(FDInfo.SUCCESS_FORMAT.format(endtime, duration, comm, pid,
                                                   name, ret, filename))
            else:
                errName = errno.errorcode[-ret]
                print(FDInfo.FAILURE_FORMAT.format(endtime, duration, comm, pid,
                                                   name, ret, errName, filename))


        if self.isInteractive and failed and not self.noColor:
            sys.stdout.write(FDInfo.NORMAL_WHITE)

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
    parser.add_argument('--failed', action='store_true',
                        help='Display only failed syscalls')
    parser.add_argument('-d', '--duration', type=int, default='-1',
                        help='Minimum duration in ms of syscalls to display')
    parser.add_argument('--no-color', action='store_true',
                        help='Disable color output')
    parser.add_argument('-e', '--errname', type=str,
                        help='Only display syscalls whose return value matches\
                        that corresponding to the given errno name')

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

    if args.errname:
        errNumber = parse_errname(args.errname)
    else:
        errNumber = None

    c = FDInfo(traces, args.prefix, isOutputEnabled, args.pid, args.pname,
               args.failed, args.duration, sys.stdout.isatty(), args.no_color, errNumber)

    c.run(args)

    traces.remove_trace(handle)
