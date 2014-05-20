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
from babeltrace import *
from LTTngAnalyzes.common import *
from LTTngAnalyzes.sched import *
from LTTngAnalyzes.syscalls import *

class NetTop():
    def __init__(self, traces, isMeasured):
        self.traces = traces
        self.isMeasured = isMeasured
        self.cpus = {}
        self.tids = {}
        self.syscalls = {}

    def process_event(self, event, sched, syscall):
        if event.name == 'sched_switch':
            sched.switch(event)
        elif event.name == 'sched_process_fork':
            sched.process_fork(event)
        elif event.name[0:4] == 'sys_':
            syscall.entry(event)
        elif event.name == 'exit_syscall':
            syscall.exit(event, False)

    def run(self, args):
        sched = Sched(self.cpus, self.tids)
        syscall = Syscalls(self.cpus, self.tids, self.syscalls)

        for event in self.traces.events:
            self.process_event(event, sched, syscall)

        self.output()

    def output(self):
        transferred = {}

        for tid in self.tids.keys():
            transferred[tid] = 0;

            for fd in self.tids[tid].fds.values():
                if fd.filename.startswith('socket'):
                    if self.isMeasured['up']:
                        transferred[tid] += fd.write
                    if self.isMeasured['down']:
                        transferred[tid] += fd.read

        for tid in transferred.keys():
            print(tid, self.tids[tid].comm, transferred[tid])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Network usage \
    analysis by process')
    parser.add_argument('path', metavar='<path/to/trace>', help='Trace path')
    parser.add_argument('-t', '--type', type=str, default='all',
                        help='Types of network IO to measure. Possible values:\
                        all, up, down')

    args = parser.parse_args()

    types = args.type.split(',')

    possibleTypes = ['up', 'down']

    if 'all' in types:
        isMeasured = { x: True for x in possibleTypes }
    else:
        isMeasured = { x: False for x in possibleTypes }
        for type in types:
            if type in possibleTypes:
                isMeasured[type] = True
            else:
                print('Invalid type:', type)
                parser.print_help()
                sys.exit(1)


    traces = TraceCollection()
    handle = traces.add_trace(args.path, 'ctf')

    c = NetTop(traces, isMeasured)
    c.run(args)

    traces.remove_trace(handle)
