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

import sys, argparse, errno, json, os.path
from babeltrace import *
from LTTngAnalyzes.common import *
from LTTngAnalyzes.sched import *
from LTTngAnalyzes.statedump import *
from LTTngAnalyzes.syscalls import *
from pymongo import MongoClient

NS_IN_S = 1000000000
NS_IN_MS = 1000000
NS_IN_US = 1000

def parse_errname(errname):
    errname = errname.upper()

    try:
        err_number = getattr(errno, errname)
    except AttributeError:
        print('Invalid errno name: ' + errname)
        sys.exit(1)

    return err_number

def parse_duration(duration):
    """Receives a numeric string with time unit suffix
    Returns an int representing a duration in nanoseconds"""

    # default case is no duration is entered by user
    if duration == '-1':
        return -1

    if duration.endswith('ns'):
        return int(duration[0:-2])
    elif duration.endswith('us'):
        return int(float(duration[0:-2]) * NS_IN_US)
    elif duration.endswith('ms'):
        return int(float(duration[0:-2]) * NS_IN_MS)
    elif duration.endswith('s'):
        return int(float(duration[0:-1]) * NS_IN_S)
    else:
        print('Invalid duration: ' + duration)
        sys.exit(1)


class FDInfo():
    DUMP_FORMAT = '{0:18} {1:20} {2:<8} {3:20} {4:60}'
    SUCCESS_FORMAT = '{0:18} ({1:8f}) {2:20} {3:<8} {4:15} res={5:<3} {6:60}'
    FAILURE_FORMAT = '{0:18} ({1:8f}) {2:20} {3:<8} {4:15} res={5:<3} ({6}) \
    {7:60}'
    FAILURE_RED = '\033[31m'
    NORMAL_WHITE = '\033[37m'

    def __init__(self, args, traces, output_enabled, err_number):
        self.args = args

        self.traces = traces
        self.output_enabled = output_enabled
        self.err_number = err_number

        self.is_interactive = sys.stdout.isatty()

        self.cpus = {}
        self.tids = {}
        self.disks = {}
        self.syscalls = {}

        self.latencies = []
        # Stores metadata about processes when outputting to json
        # Keys: PID, values: {pname, fds}
        self.json_metadata = {}

    def process_event(self, event, sched, syscall, statedump):
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
            if self.output_enabled['dump']:
                self.output_dump(event)

    def handle_syscall_exit(self, event, syscall, started=1):
        cpu_id = event['cpu_id']
        if not cpu_id in self.cpus:
            return

        cpu = self.cpus[cpu_id]
        if cpu.current_tid == -1:
            return

        current_syscall = self.tids[cpu.current_tid].current_syscall
        if len(current_syscall.keys()) == 0:
            return

        name = current_syscall['name']
        if name in Syscalls.OPEN_SYSCALLS and self.output_enabled['open'] or\
           name in Syscalls.CLOSE_SYSCALLS and self.output_enabled['close'] or\
           name in Syscalls.READ_SYSCALLS and self.output_enabled['read'] or\
           name in Syscalls.WRITE_SYSCALLS and self.output_enabled['write']:
            self.output_fd_event(event, current_syscall)

        syscall.exit(event, started)

    def run(self):
        '''Process the trace'''

        sched = Sched(self.cpus, self.tids)
        syscall = Syscalls(self.cpus, self.tids, self.syscalls)
        statedump = Statedump(self.tids, self.disks)

        for event in self.traces.events:
            self.process_event(event, sched, syscall, statedump)

        if self.args.json_latencies:
            self.output_json_latencies()

        if self.args.mongo:
            self.store_mongo_latencies()

    def output_json_latencies(self):
        f = open(os.path.join(self.args.json_latencies, 'latencies.json'), 'w')
        json.dump(self.latencies, f)
        f.close()

        f = open(os.path.join(self.args.json_latencies, 'pid_metadata.json'), 'w')
        json.dump(self.json_metadata, f)
        f.close()

    def store_mongo_latencies(self):
        client = MongoClient('localhost', 27017)
        db = client.analyses
        collection = db.fdinfo

        collection.insert(self.json_metadata)

    def output_dump(self, event):
        # dump events can't fail, and don't have a duration, so ignore
        if self.args.failed or self.err_number or self.args.duration > 0:
            return

        pid = event['pid']
        if self.args.pid >= 0 and self.args.pid != pid:
            return

        comm = self.tids[pid].comm
        if self.args.pname is not None and self.args.pname != comm:
            return

        name = event.name
        if args.syscall and args.syscall != name:
            return

        filename = event['filename']

        endtime = event.timestamp
        if self.args.start and endtime < self.args.start:
            return
        if self.args.end and endtime > self.args.end:
            return

        if not self.args.unixtime:
            endtime = ns_to_hour_nsec(endtime)
        else:
            endtime = '{:.9f}'.format(endtime / NS_IN_S)

        if filename.startswith(self.args.prefix) and not self.args.quiet:
            print(FDInfo.DUMP_FORMAT.format(endtime, comm, pid, name, filename))

    def output_fd_event(self, exit_event, entry):
        ret = exit_event['ret']
        failed = ret < 0

        if self.args.failed and not failed:
            return

        if self.err_number and ret != -err_number:
            return

        pid = self.cpus[exit_event['cpu_id']].current_tid
        if self.args.pid >= 0 and self.args.pid != pid:
            return

        comm = self.tids[pid].comm
        if self.args.pname is not None and self.args.pname != comm:
            return

        filename = entry['filename']
        if filename is None:
            return

        name = entry['name']

        if args.syscall and args.syscall != name:
            return

        if self.args.start and entry['start'] < self.args.start:
            return

        if self.args.end and exit_event.timestamp > self.args.end:
            return

        endtime = exit_event.timestamp
        if not self.args.unixtime:
            endtime = ns_to_hour_nsec(endtime)
        else:
            endtime = '{:.9f}'.format(endtime / 1000000000)

        duration_ns = (exit_event.timestamp - entry['start'])

        if self.args.duration > 0 and duration_ns < self.args.duration:
            return

        duration = duration_ns / 1000000000

        if self.args.json_latencies or self.args.mongo:
            self.log_fd_event_json(pid, comm, entry, name, duration_ns, filename)

        if self.is_interactive and failed and not self.args.no_color:
            sys.stdout.write(FDInfo.FAILURE_RED)

        if filename.startswith(self.args.prefix) and not self.args.quiet:
            if not failed:
                print(FDInfo.SUCCESS_FORMAT.format(endtime, duration, comm, pid,
                                                   name, ret, filename))
            else:
                try:
                    err_name = errno.errorcode[-ret]
                    print(FDInfo.FAILURE_FORMAT.format(endtime, duration, comm, pid,
                        name, ret, err_name,
                        filename))
                except KeyError:
                    print("Invalid error code:", -ret)

        if self.is_interactive and failed and not self.args.no_color:
            sys.stdout.write(FDInfo.NORMAL_WHITE)

    def log_fd_event_json(self, pid, comm, entry, name, duration_ns, filename):
        if str(pid) not in self.json_metadata:
            self.json_metadata[str(pid)] = {'pname': comm, 'fds': {}}
        # Fix process name
        elif self.json_metadata[str(pid)]['pname'] != comm:
            self.json_metadata[str(pid)]['pname'] = comm

        fd = None

        if 'fd' in entry.keys():
            fd = entry['fd'].fd
        elif 'fd_in' in entry.keys():
            fd = entry['fd_in'].fd

        if fd:
            fdtype = FDType.unknown

            if fd in self.tids[pid].fds:
                fdtype = self.tids[pid].fds[fd].fdtype

            if str(fd) not in self.json_metadata[str(pid)]['fds']:
                self.json_metadata[str(pid)]['fds'][str(fd)] = {}
                self.json_metadata[str(pid)]['fds'][str(fd)]['filename'] = filename
                self.json_metadata[str(pid)]['fds'][str(fd)]['fdtype'] = fdtype

        category = Syscalls.get_syscall_category(name)
        self.latencies.append([entry['start'], duration_ns, pid, category, fd])


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
    parser.add_argument('-d', '--duration', type=str, default='-1',
                        help='Minimum duration in ms of syscalls to display')
    parser.add_argument('-e', '--errname', type=str,
                        help='Only display syscalls whose return value matches\
                        that corresponding to the given errno name')
    parser.add_argument('--syscall', type=str, default=None,
                        help='Name of syscall to display')
    parser.add_argument('--start', type=int, default=None,
                        help='Start time from which to display events (unix\
                        time)')
    parser.add_argument('--end', type=int, default=None,
                        help='End time after which events are not displayed\
                        (unix time)')
    parser.add_argument('--failed', action='store_true',
                        help='Display only failed syscalls')
    parser.add_argument('--unixtime', action='store_true',
                        help='Display timestamps in unix time format')
    parser.add_argument('--no-color', action='store_true',
                        help='Disable color output')
    parser.add_argument('--json-latencies', type=str, default=None,
                        help='Store latencies as JSON in specified directory')
    parser.add_argument('--mongo', action='store_true',
                        help='Store latencies into MongoDB')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Don\'t output fd events to stdout')

    args = parser.parse_args()

    types = args.type.split(',')

    possibleTypes = ['open', 'close', 'read', 'write', 'dump']

    if 'all' in types:
        output_enabled = {x: True for x in possibleTypes}
    else:
        output_enabled = {x: False for x in possibleTypes}
        for event_type in types:
            if event_type in possibleTypes:
                output_enabled[event_type] = True
            else:
                print('Invalid type:', event_type)
                parser.print_help()
                sys.exit(1)

    if args.syscall and not args.syscall.startswith('sys_'):
        args.syscall = 'sys_' + args.syscall

    traces = TraceCollection()
    handle = traces.add_trace(args.path, 'ctf')
    if handle is None:
        sys.exit(1)

    if args.errname:
        err_number = parse_errname(args.errname)
    else:
        err_number = None

    # Convert start/endtime from seconds to nanoseconds
    if args.start:
        args.start = args.start * 1000000000
    if args.end:
        args.end = args.end * 1000000000

    # Parse duration option
    args.duration = parse_duration(args.duration)

    analyser = FDInfo(args, traces, output_enabled, err_number)

    analyser.run()

    traces.remove_trace(handle)
