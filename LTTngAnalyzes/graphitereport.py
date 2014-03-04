from LTTngAnalyzes.common import *
import operator
import os
import sys
import time
import platform 
import subprocess
from socket import socket

CARBON_SERVER = '10.0.3.185'
CARBON_PORT = 2003

class GraphiteReport():
    def __init__(self, trace_start_ts, trace_end_ts, cpus, tids, syscalls):
        self.trace_start_ts = trace_start_ts
        self.trace_end_ts = trace_end_ts
        self.cpus = cpus
        self.tids = tids
        self.syscalls = syscalls
        self.hostname = os.uname()[1]

    def report(self, begin_ns, end_ns, final, args):
        if not (args.info or args.cpu or args.tid or args.global_syscalls \
                or args.tid_syscalls):
            return

        sock = socket()
        try:
            sock.connect( (CARBON_SERVER,CARBON_PORT) )
        except:
            print("Couldn't connect to %(server)s on port %(port)d, is " \
                  "carbon-agent.py running?" % { 'server':CARBON_SERVER,
                          'port':CARBON_PORT })
            sys.exit(1)

        total_ns = end_ns - begin_ns

        if args.cpu:
            self.per_cpu_report(total_ns, end_ns, sock)

    def per_cpu_report(self, total_ns, end_ns, sock):
        total_cpu_pc = 0
        nb_cpu = len(self.cpus.keys())
        lines = []
        for cpu in self.cpus.keys():
            cpu_total_ns = self.cpus[cpu].cpu_ns
            cpu_pc = self.cpus[cpu].cpu_pc
            total_cpu_pc += cpu_pc
            lines.append("hosts.%s.cpu.%d.10sec %d %lu" % (self.hostname, cpu, cpu_pc,
                end_ns/NSEC_PER_SEC))
        lines.append("hosts.%s.cpu.total.10sec %d %lu" % (self.hostname,
            total_cpu_pc/nb_cpu, end_ns/NSEC_PER_SEC))
        message = '\n'.join(lines) + '\n' #all lines must end in a newline
        sock.sendall(message.encode())
        print("Sent at", end_ns/NSEC_PER_SEC)
