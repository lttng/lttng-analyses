import os
import sys
from socket import socket
from LTTngAnalyzes.common import NSEC_PER_SEC

CARBON_SERVER = '10.0.3.185'
CARBON_PORT = 2003


class GraphiteReport():
    def __init__(self, trace_start_ts, trace_end_ts, cpus, tids,
                 syscalls, disks, ifaces):
        self.trace_start_ts = trace_start_ts
        self.trace_end_ts = trace_end_ts
        self.cpus = cpus
        self.tids = tids
        self.syscalls = syscalls
        self.disks = disks
        self.ifaces = ifaces
        self.hostname = os.uname()[1]

    def report(self, begin_ns, end_ns, final, args):
        if not (args.info or args.cpu or args.tid or args.global_syscalls
                or args.tid_syscalls):
            return

        sock = socket()
        try:
            sock.connect((CARBON_SERVER, CARBON_PORT))
        except:
            print("Couldn't connect to %(server)s on port %(port)d, is "
                  "carbon-agent.py running?"
                  % {'server': CARBON_SERVER, 'port': CARBON_PORT})
            sys.exit(1)

        total_ns = end_ns - begin_ns

        if args.cpu:
            self.per_cpu_report(total_ns, end_ns, sock)
        if args.disk:
            self.per_disk_report(end_ns, sock)
        if args.net:
            self.per_iface_report(end_ns, sock)
        # if args.tid:
        #    self.per_tid_report(end_ns, total_ns, sock)

    def per_cpu_report(self, total_ns, end_ns, sock):
        total_cpu_pc = 0
        nb_cpu = len(self.cpus.keys())
        lines = []
        for cpu in self.cpus.keys():
            cpu_pc = self.cpus[cpu].cpu_pc
            total_cpu_pc += cpu_pc
            lines.append("hosts.%s.cpu.cpu%d %d %lu" % (self.hostname,
                                                        cpu, cpu_pc,
                                                        end_ns/NSEC_PER_SEC))
        lines.append("hosts.%s.cpu.totalcpu %d %lu"
                     % (self.hostname, total_cpu_pc/nb_cpu,
                        end_ns/NSEC_PER_SEC))
        message = '\n'.join(lines) + '\n'  # all lines must end in a newline
        sock.sendall(message.encode())
        print("Sent cpu at", end_ns/NSEC_PER_SEC)

    def per_disk_report(self, end_ns, sock):
        lines = []
        ts = end_ns/NSEC_PER_SEC
        for dev in self.disks:
            lines.append("hosts.%s.disk.%d.rq %d %lu"
                         % (self.hostname, dev,
                            self.disks[dev].nr_requests, ts))
            lines.append("hosts.%s.disk.%d.sectors %d %lu"
                         % (self.hostname, dev, self.disks[dev].nr_sector, ts))
            if self.disks[dev].completed_requests > 0:
                total = (self.disks[dev].request_time /
                         self.disks[dev].completed_requests)
                lines.append("hosts.%s.disk.%d.latency %d %lu" %
                             (self.hostname, dev, total, ts))
        message = '\n'.join(lines) + '\n'  # all lines must end in a newline
        sock.sendall(message.encode())
        print("Sent block at", end_ns/NSEC_PER_SEC)

    def per_iface_report(self, end_ns, sock):
        lines = []
        ts = end_ns/NSEC_PER_SEC
        for iface in self.ifaces:
            lines.append("hosts.%s.net.%s.recv_bytes %d %lu"
                         % (self.hostname, iface,
                            self.ifaces[iface].recv_bytes, ts))
            lines.append("hosts.%s.net.%s.recv_packets %d %lu"
                         % (self.hostname, iface,
                            self.ifaces[iface].recv_packets, ts))
            lines.append("hosts.%s.net.%s.send_bytes %d %lu"
                         % (self.hostname, iface,
                            self.ifaces[iface].send_bytes, ts))
            lines.append("hosts.%s.net.%s.send_packets %d %lu"
                         % (self.hostname, iface,
                            self.ifaces[iface].send_packets, ts))
        message = '\n'.join(lines) + '\n'  # all lines must end in a newline
        sock.sendall(message.encode())
        print("Sent net at", end_ns/NSEC_PER_SEC)

    def per_tid_report(self, end_ns, total_ns, sock):
        lines = []
        ts = end_ns/NSEC_PER_SEC
        for tid in self.tids.values():
            if tid.tid == 0:
                continue
            lines.append("hosts.%s.tid.%s-%d %d %lu"
                         % (self.hostname, tid.comm.replace("/", "|"),
                            tid.tid, ((tid.cpu_ns * 100) / total_ns), ts))
        message = '\n'.join(lines) + '\n'  # all lines must end in a newline
        sock.sendall(message.encode())
        print("Sent TIDs at", end_ns/NSEC_PER_SEC)
