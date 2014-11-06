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

import argparse
import errno
import json
from os.path import join
import socket
import sys
from collections import OrderedDict
try:
    from babeltrace import TraceCollection
except ImportError:
    # quick fix for debian-based distros
    sys.path.append("/usr/local/lib/python%d.%d/site-packages" %
                    (sys.version_info.major, sys.version_info.minor))
    from babeltrace import TraceCollection
from LTTngAnalyzes.common import FDType, ns_to_hour_nsec, NSEC_PER_SEC
from LTTngAnalyzes.sched import Sched
from LTTngAnalyzes.statedump import Statedump
from LTTngAnalyzes.syscalls import Syscalls, IOCategory
try:
    from pymongo import MongoClient
    from pymongo.errors import CollectionInvalid
except ImportError:
    nomongolib = 1

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

        self.fd_events = []
        # Stores metadata about processes when outputting to json
        # Keys: PID, values: {pname, fds, threads}
        self.json_metadata = {}
        # Used to identify session in database
        if self.args.path[-1] == '/':
            self.session_name = self.args.path.split('/')[-3]
        else:
            self.session_name = self.args.path.split('/')[-2]
        # Hyphens in collections names are an incovenience in mongo
        self.session_name = self.session_name.replace('-', '_')

    def process_event(self, event, sched, syscall, statedump):
        if event.name == 'sched_switch':
            sched.switch(event)
        elif event.name.startswith('sys_') or \
                event.name.startswith('syscall_entry_'):
            syscall.entry(event)
        elif event.name == 'exit_syscall' or \
                event.name.startswith('syscall_exit_'):
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
        if cpu_id not in self.cpus:
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

        if self.args.json:
            self.output_json()

        if self.args.mongo:
            self.store_mongo()

        if self.args.graphite:
            self.store_graphite()

        if self.args.localfile:
            self.store_localfile()

    def output_json(self):
        fd_events_name = 'fd_events_' + self.session_name + '.json'
        fd_events_path = join(self.args.json, fd_events_name)
        f = open(fd_events_path, 'w')
        json.dump(self.fd_events, f)
        f.close()

        f = open(join(self.args.json, 'metadata.json'), 'w')
        json.dump(self.json_metadata, f)
        f.close()

    def store_graphite(self):
        sock = None
        try:
            sock = socket.create_connection((self.args.graphite_host,
                                             self.args.graphite_port))
        except:
            print("Couldn't connect to %(server)s on port %(port)d, is "
                  "carbon-agent.py running?" % {'server':
                                                self.args.graphite_host,
                                                'port':
                                                self.args.graphite_port})
            sys.exit(1)

        lines = []
        for event in self.fd_events:
            ts = event["ts_start"]/NSEC_PER_SEC
            if event["category"] == IOCategory.write:
                l = "hosts.test.latencies.write %d %lu" % \
                    (event["duration"]/(NSEC_PER_SEC), ts)
            elif event["category"] == IOCategory.read:
                l = "hosts.test.latencies.read %d %lu" % \
                    (event["duration"]/(NSEC_PER_SEC), ts)
            else:
                continue
            lines.append(l)
        message = '\n'.join(lines) + '\n'  # all lines must end in a newline
        sock.sendall(message.encode())

    def store_localfile(self):
        nb_read = 0
        total_read = 0
        nb_write = 0
        total_write = 0
        pid_latencies = {}
        for event in self.fd_events:
            if args.pid_latency_list and str(event["pid"]) in \
                    args.pid_latency_list:
                if not event["pid"] in pid_latencies.keys():
                    pid_latencies[event["pid"]] = {}
                    pid_latencies[event["pid"]]["r"] = 0
                    pid_latencies[event["pid"]]["nb_r"] = 0
                    pid_latencies[event["pid"]]["w"] = 0
                    pid_latencies[event["pid"]]["nb_w"] = 0
            if event["category"] == IOCategory.write:
                total_write += event["duration"]
                nb_write += 1
                if args.pid_latency_list and str(event["pid"]) in \
                        args.pid_latency_list:
                    pid_latencies[event["pid"]]["w"] += event["duration"]
                    pid_latencies[event["pid"]]["nb_w"] += 1
            elif event["category"] == IOCategory.read:
                total_read += event["duration"]
                nb_read += 1
                if args.pid_latency_list and str(event["pid"]) in \
                        args.pid_latency_list:
                    pid_latencies[event["pid"]]["r"] += event["duration"]
                    pid_latencies[event["pid"]]["nb_r"] += 1
            else:
                continue
        f = open(join(args.localfile, "avg_w_latency"), "w")
        f.write("%f\n" % ((total_write/nb_write) / (NSEC_PER_SEC / 1000000)))
        f.close()

        f = open(join(args.localfile, "avg_r_latency"), "w")
        f.write("%f\n" % ((total_read/nb_read) / (NSEC_PER_SEC / 1000000)))
        f.close()

        for p in pid_latencies.keys():
            r = pid_latencies[p]["r"]
            nb_r = pid_latencies[p]["nb_r"]
            w = pid_latencies[p]["w"]
            nb_w = pid_latencies[p]["nb_w"]
            if nb_r > 0:
                f = open(join(args.localfile, "%d_r_latency" % (p)), "w")
                f.write("%f\n" % ((r/nb_r) / (NSEC_PER_SEC / 1000000)))
                f.close()
            if nb_w > 0:
                f = open(join(args.localfile, "%d_w_latency" % (p)), "w")
                f.write("%f\n" % ((w/nb_w) / (NSEC_PER_SEC / 1000000)))
                f.close()

    def store_mongo(self):
        client = MongoClient(self.args.mongo_host, self.args.mongo_port)
        db = client.analyses

        fd_events_name = 'fd_events_' + self.session_name
        metadata_name = 'metadata_' + self.session_name

        try:
            db.create_collection(fd_events_name)
        except CollectionInvalid as ex:
            print('Failed to create collection: ')
            print(ex)
            print('Data will not be stored to MongoDB')
            return

        for event in self.fd_events:
            db[fd_events_name].insert(event)

        # Ascending timestamp index
        db[fd_events_name].create_index('ts_start')

        if metadata_name not in db.collection_names():
            try:
                db.create_collection(metadata_name)
            except CollectionInvalid as ex:
                print('Failed to create collection: ')
                print(ex)
                print('Metadata will not be stored to MongoDB')
                return

            db.sessions.insert({'name': self.session_name})

        for pid in self.json_metadata:
            metadatum = self.json_metadata[pid]
            metadatum['pid'] = pid
            db[metadata_name].update({'pid': pid}, metadatum, upsert=True)

        # Ascending PID index
        db[metadata_name].create_index('pid')

    def output_dump(self, event):
        # dump events can't fail, and don't have a duration, so ignore
        if self.args.failed or self.err_number or self.args.duration > 0:
            return

        # using tid as variable name for consistency with other events
        tid = event['pid']
        if self.args.tid >= 0 and self.args.tid != tid:
            return

        comm = self.tids[tid].comm
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
            print(FDInfo.DUMP_FORMAT.format(endtime, comm, tid, name,
                                            filename))

    def output_fd_event(self, exit_event, entry):
        ret = exit_event['ret']
        failed = ret < 0

        if self.args.failed and not failed:
            return

        if self.err_number and ret != -err_number:
            return

        tid = self.cpus[exit_event['cpu_id']].current_tid
        if self.args.tid >= 0 and self.args.tid != tid:
            return

        pid = self.tids[tid].pid
        if pid == -1:
            pid = tid

        comm = self.tids[tid].comm
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
            endtime = '{:.9f}'.format(endtime / NS_IN_S)

        duration_ns = (exit_event.timestamp - entry['start'])

        if self.args.duration > 0 and duration_ns < self.args.duration:
            return

        duration = duration_ns / NS_IN_S

        if self.args.json or self.args.mongo or self.args.graphite or \
                self.args.localfile:
            self.log_fd_event_json(tid, pid, comm, entry, name, duration_ns,
                                   filename, ret)

        if self.is_interactive and failed and not self.args.no_color:
            sys.stdout.write(FDInfo.FAILURE_RED)

        if filename.startswith(self.args.prefix) and not self.args.quiet:
            if not failed:
                print(FDInfo.SUCCESS_FORMAT.format(endtime, duration, comm,
                                                   tid, name, ret, filename))
            else:
                try:
                    err_name = errno.errorcode[-ret]
                    print(FDInfo.FAILURE_FORMAT.format(endtime, duration, comm,
                                                       tid, name, ret,
                                                       err_name, filename))
                except KeyError:
                    print('Invalid error code:', -ret)

        if self.is_interactive and failed and not self.args.no_color:
            sys.stdout.write(FDInfo.NORMAL_WHITE)

    def log_fd_event_json(self, tid, pid, comm, entry, name, duration_ns,
                          filename, ret):
        self.track_thread(tid, pid, comm)

        fd = None
        fd_in = None
        fd_out = None

        if 'fd' in entry.keys():
            fd = entry['fd'].fd
        elif 'fd_in' in entry.keys():
            fd_in = entry['fd_in'].fd
            fd_out = entry['fd_out'].fd

        if fd:
            self.track_fd(fd, filename, tid, pid, entry)
        elif fd_in and fd_out:
            self.track_fd(fd_in, filename, tid, pid, entry)
            self.track_fd(fd_out, filename, tid, pid, entry)

        category = Syscalls.get_syscall_category(name)

        fd_event = {'ts_start': entry['start'],
                    'duration': duration_ns,
                    'tid': tid,
                    'pid': pid,
                    'category': category}

        if fd is not None:
            fd_event['fd'] = fd
        elif fd_in is not None and fd_out is not None:
            fd_event['fd_in'] = fd_in
            fd_event['fd_out'] = fd_out

        if ret < 0:
            fd_event['errno'] = -ret
        else:
            if name in ['sys_splice', 'sys_sendfile64']:
                fd_event['read'] = ret
                fd_event['write'] = ret
            elif name in Syscalls.READ_SYSCALLS:
                fd_event['read'] = ret
            elif name in Syscalls.WRITE_SYSCALLS:
                fd_event['write'] = ret

        self.fd_events.append(fd_event)

    def track_thread(self, tid, pid, comm):
        # Dealing with plain old process
        if pid == tid:
            if pid not in self.json_metadata:
                self.json_metadata[pid] = {
                    'pname': comm,
                    'fds': {},
                    'threads': {}
                }
            else:
                if self.json_metadata[pid]['pname'] != comm:
                    self.json_metadata[pid]['pname'] = comm
        # Dealing with a thread
        else:
            if pid not in self.json_metadata:
                self.json_metadata[pid] = {
                    'pname': 'unknown',
                    'fds': {},
                    'threads': {}
                }

            tid_str = str(tid)
            if tid_str not in self.json_metadata[pid]['threads']:
                self.json_metadata[pid]['threads'][tid_str] = {
                    'pname': comm
                }
            else:
                if self.json_metadata[pid]['threads'][tid_str]['pname'] \
                        != comm:
                    self.json_metadata[pid]['threads'][tid_str]['pname'] = comm

    def track_fd(self, fd, filename, tid, pid, entry):
        fd_str = str(fd)
        fdtype = FDType.unknown

        if fd in self.tids[tid].fds:
            fdtype = self.tids[tid].fds[fd].fdtype

        fd_metadata = {}
        fd_metadata['filename'] = filename
        fd_metadata['fdtype'] = fdtype

        if str(fd) not in self.json_metadata[pid]['fds']:
            fds = self.json_metadata[pid]['fds']
            fds[fd_str] = OrderedDict()
            fds[fd_str][str(entry['start'])] = fd_metadata
        else:
            chrono_fd = self.json_metadata[pid]['fds'][fd_str]
            last_ts = next(reversed(chrono_fd))
            if filename != chrono_fd[last_ts]['filename']:
                chrono_fd[str(entry['start'])] = fd_metadata


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='FD syscalls analysis')
    parser.add_argument('path', metavar='<path/to/trace>', help='Trace path')
    parser.add_argument('-p', '--prefix', type=str, default='',
                        help='Prefix in which to search')
    parser.add_argument('-t', '--type', type=str, default='all',
                        help='Types of events to display. Possible values:\
                        all, open, close, read, write dump')
    parser.add_argument('--tid', type=int, default='-1',
                        help='TID for which to display events')
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
    parser.add_argument('--json', type=str, default=None,
                        help='Store FD events as JSON in specified directory')
    parser.add_argument('--mongo', type=str, default=None,
                        help='Store FD events into MongoDB at specified ip\
                        and port')
    parser.add_argument('--graphite', type=str, default=None,
                        help='Store FD events into graphite at specified ip\
                    and port')
    parser.add_argument('--localfile', type=str, default=None,
                        help='Store average latencies in local files '
                        '(one file per metric)')
    parser.add_argument('--pidlatencies', type=str, default=None,
                        help='Compute R/W latencies for these processes for '
                             'localfile mode')
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
        args.start = args.start * NS_IN_S
    if args.end:
        args.end = args.end * NS_IN_S

    # Parse duration option
    args.duration = parse_duration(args.duration)

    if args.mongo:
        if nomongolib == 1:
            print("Missing pymongo library")
            sys.exit(1)
        try:
            (args.mongo_host, args.mongo_port) = args.mongo.split(':')
            socket.inet_aton(args.mongo_host)
            args.mongo_port = int(args.mongo_port)
        except ValueError:
            print('Invalid MongoDB address format: ', args.mongo)
            print('Expected format: IPV4:PORT')
            sys.exit(1)
        except socket.error:
            print('Invalid MongoDB ip ', args.mongo_host)
            sys.exit(1)

    if args.graphite:
        try:
            (args.graphite_host, args.graphite_port) = args.graphite.split(':')
            socket.inet_aton(args.graphite_host)
            args.graphite_port = int(args.graphite_port)
        except ValueError:
            print('Invalid graphite address format: ', args.graphite)
            print('Expected format: IPV4:PORT')
            sys.exit(1)
        except socket.error:
            print('Invalid graphite ip ', args.graphite_host)
            sys.exit(1)

    if args.pidlatencies:
        args.pid_latency_list = args.pidlatencies.split(",")
    else:
        args.pid_latency_list = None

    analyser = FDInfo(args, traces, output_enabled, err_number)

    analyser.run()

    traces.remove_trace(handle)
