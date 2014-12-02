#!/usr/bin/env python3
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

import sys
import argparse
import os
import sqlite3
try:
    from babeltrace import TraceCollection
except ImportError:
    # quick fix for debian-based distros
    sys.path.append("/usr/local/lib/python%d.%d/site-packages" %
                    (sys.version_info.major, sys.version_info.minor))
    from babeltrace import TraceCollection
from LTTngAnalyzes.common import CPU, Process, Syscall

DB_NAME = "proc.db"


class Analyzes():
    def __init__(self, traces):
        self.traces = traces
        self.processes = {}
        self.cpus = {}

    def connect_db(self):
        self.conn = sqlite3.connect(DB_NAME)
        self.cur = self.conn.cursor()

    def init_db(self):
        self.connect_db()
        self.cur.execute("DROP TABLE IF EXISTS processes")
        self.cur.execute("CREATE TABLE processes (name TEXT)")
        self.cur.execute("DROP TABLE IF EXISTS syscalls")
        self.cur.execute("CREATE TABLE syscalls "
                         "(proc_name TEXT, syscall_name TEXT)")

        self.cur.execute("DROP TABLE IF EXISTS staging_processes")
        self.cur.execute("CREATE TABLE staging_processes (name TEXT)")
        self.cur.execute("DROP TABLE IF EXISTS staging_syscalls")
        self.cur.execute("CREATE TABLE staging_syscalls "
                         "(proc_name TEST, syscall_name TEXT)")

    def check_process(self, proc):
        self.cur.execute("SELECT * FROM processes WHERE name=:name",
                         {"name": proc})
        p = self.cur.fetchall()
        if p:
            return
        self.cur.execute("SELECT * FROM staging_processes WHERE name=:name",
                         {"name": proc})
        p = self.cur.fetchall()
        if not p:
            self.cur.execute("INSERT INTO staging_processes VALUES (:proc)",
                             {"proc": proc})

    def check_syscall(self, proc, syscall):
        self.cur.execute("SELECT * FROM syscalls WHERE proc_name=:proc_name "
                         "AND syscall_name=:syscall_name",
                         {"proc_name": proc, "syscall_name": syscall})
        p = self.cur.fetchall()
        if p:
            return
        self.cur.execute("SELECT * FROM staging_syscalls "
                         "WHERE proc_name=:proc_name "
                         "AND syscall_name=:syscall_name",
                         {"proc_name": proc, "syscall_name": syscall})
        p = self.cur.fetchall()
        if not p:
            self.cur.execute("INSERT INTO staging_syscalls VALUES(?,?)",
                             (proc, syscall))

    def add_proc(self, p):
        self.cur.execute("INSERT INTO processes VALUES (:proc)",
                         {"proc": p})
        self.cur.execute("DELETE FROM staging_processes WHERE name=:proc",
                         {"proc": p})

    def add_syscall(self, p, s):
        self.cur.execute("INSERT INTO syscalls VALUES (:proc, :syscall)",
                         {"proc": p, "syscall": s})
        self.cur.execute("DELETE FROM staging_syscalls WHERE proc_name=:proc "
                         "AND syscall_name=:syscall",
                         {"proc": p, "syscall": s})

    def review_processes(self):
        self.cur.execute("SELECT * FROM staging_processes")
        proc = self.cur.fetchall()
        if not proc:
            return
        add_all = 0
        for p in proc:
            if add_all:
                print("Adding %s" % p[0])
                self.add_proc(p[0])
                continue

            print("Found new process running: %s, "
                  "add it to the DB (Y/n/a/q) ?" % (p))
            a = sys.stdin.readline().strip()
            if a in ["y", "Y", ""]:
                self.add_proc(p[0])
            elif a == "a":
                add_all = 1
                self.add_proc(p[0])
            elif a == "q":
                return
            else:
                continue

    def review_syscalls(self):
        self.cur.execute("SELECT * FROM staging_syscalls")
        sysc = self.cur.fetchall()
        if not sysc:
            return
        add_all = 0
        for p in sysc:
            if add_all:
                print("Adding %s to %s" % (p[1], p[0]))
                self.add_syscall(p[0], p[1])
                continue

            print("Found new syscall %s for proc %s, "
                  "add it to the DB (Y/n/a/q) ?" %
                  (p[1], p[0]))
            a = sys.stdin.readline().strip()
            if a in ["y", "Y", ""]:
                self.add_syscall(p[0], p[1])
            elif a == "a":
                add_all = 1
                self.add_syscall(p[0], p[1])
            elif a == "q":
                return
            else:
                continue

    def lttng_statedump_process_state(self, event):
        name = event["name"]
        if name not in self.processes.keys():
            self.processes[name] = Process()
            self.check_process(name)

    def sched_switch(self, event):
        next_comm = event["next_comm"]
        cpu_id = event["cpu_id"]
        if cpu_id not in self.cpus.keys():
            self.cpus[cpu_id] = CPU()
        self.cpus[cpu_id].current_comm = next_comm
        if next_comm not in self.processes.keys():
            self.processes[next_comm] = Process()
            self.check_process(next_comm)

    def syscall_entry(self, event):
        cpu_id = event["cpu_id"]
        if cpu_id not in self.cpus.keys():
            return
        p = self.processes[self.cpus[cpu_id].current_comm]
        p.syscalls[event.name] = Syscall()
        self.check_syscall(self.cpus[cpu_id].current_comm, event.name)

    def run(self, args):
        for event in self.traces.events:
            if event.name == "sched_switch":
                self.sched_switch(event)
            elif event.name == "lttng_statedump_process_state":
                self.lttng_statedump_process_state(event)
            elif event.name[0:4] == "sys_":
                self.syscall_entry(event)
        self.conn.commit()
        self.review_processes()
        self.review_syscalls()
        self.conn.commit()

    def report(self):
        for p in self.processes.keys():
            print(p)
            for s in self.processes[p].syscalls.keys():
                print("    %s" % s)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Activity tracker')
    parser.add_argument('path', metavar="<path/to/trace>", help='Trace path')
    parser.add_argument('--reset', action="store_true",
                        help='Destroy and init the database')
    parser.add_argument('--accept', action="store_true",
                        help='Accept all (non-interactive)')
    parser.add_argument('--report', action="store_true",
                        help='Report the difference between the DB '
                             '(non-interactive)')
    args = parser.parse_args()

    traces = TraceCollection()
    handle = traces.add_traces_recursive(args.path, "ctf")
    if handle is None:
        sys.exit(1)

    c = Analyzes(traces)
    if not os.path.isfile(DB_NAME):
        print("Creating the database for the first time")
        c.init_db()
    elif args.reset:
        print("Resetting the database")
        c.init_db()
    else:
        c.connect_db()

    c.run(args)

    for h in handle.values():
        traces.remove_trace(h)
