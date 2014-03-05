from LTTngAnalyzes.common import *
import operator

#class CPUComplexEncoder(json.JSONEncoder):
#    def default(self, obj):
#        if isinstance(obj, CPU):
#            return obj.cpu_pc
#        # Let the base class default method raise the TypeError
#        return json.JSONEncoder.default(self, obj)

class TextReport():
    def __init__(self, trace_start_ts, trace_end_ts, cpus, tids, syscalls, disks):
        self.trace_start_ts = trace_start_ts
        self.trace_end_ts = trace_end_ts
        self.cpus = cpus
        self.tids = tids
        self.syscalls = syscalls
        self.disks = disks

    def text_trace_info(self):
        total_ns = self.trace_end_ts - self.trace_start_ts
        print("### Trace info ###")
        print("Start : %lu\nEnd: %lu" % (self.trace_start_ts, self.trace_end_ts))
        print("Total ns : %lu" % (total_ns))
        print("Total : %lu.%0.09lus" % (total_ns / NSEC_PER_SEC,
            total_ns % NSEC_PER_SEC))

    def report(self, begin_ns, end_ns, final, args):
        if not (args.info or args.cpu or args.tid or args.global_syscalls \
                or args.tid_syscalls or args.disk):
            return
        if args.cpu or args.tid or args.global_syscalls or args.tid_syscalls or args.disk:
            print("[%lu:%lu]" % (begin_ns/NSEC_PER_SEC, end_ns/NSEC_PER_SEC))

        total_ns = end_ns - begin_ns

        if args.info and final:
            self.text_trace_info()
            print("")
        if args.cpu:
            self.text_per_cpu_report(total_ns)
            print("")
        if args.tid:
            self.text_per_tid_report(total_ns, args.display_proc_list,
                    limit=args.top, syscalls=args.tid_syscalls)
            print("")
        if args.global_syscalls:
            self.text_global_syscall_report()
            print("")
        if args.disk:
            self.text_disks_report(total_ns)
            print("")

    def text_disks_report(self, total_ns):
        print("### Disks stats ###")
        for dev in self.disks:
            if self.disks[dev].completed_requests == 0:
                totalstr = "0 completed requests"
            else:
                total = (self.disks[dev].request_time / self.disks[dev].completed_requests) / MSEC_PER_NSEC
                totalstr = ("%d completed requests (%0.04fms/sector)" % (self.disks[dev].completed_requests, total))
            print("Dev %d, %d requests, %d sectors, %s" %
                    (dev, self.disks[dev].nr_requests,
                        self.disks[dev].nr_sector, totalstr))

    def text_global_syscall_report(self):
        print("### Global syscall ###")
        for syscall in sorted(self.syscalls.values(),
                key=operator.attrgetter("count"), reverse=True):
            if syscall.count == 0:
                continue
            print("%s : %d" % (syscall.name[4:], syscall.count))

    def text_per_tid_report(self, total_ns, proc_list, limit=0, syscalls=0):
        print("### Per-TID Usage ###")
        count = 0
        for tid in sorted(self.tids.values(),
                key=operator.attrgetter('cpu_ns'), reverse=True):
            if len(proc_list) > 0 and tid.comm not in proc_list:
                continue
            print("%s (%d) : %0.02f%%" % (tid.comm, tid.tid,
                ((tid.cpu_ns * 100) / total_ns)), end="")
            if tid.migrate_count > 0:
                print(""" (%d migration(s))""" % tid.migrate_count)
            else:
                print("")
            count = count + 1
            if syscalls:
                for syscall in sorted(tid.syscalls.values(),
                        key=operator.attrgetter('count'), reverse=True):
                    if syscall.count == 0:
                        continue
                    print(" - %s : %d" % (syscall.name[4:], syscall.count))
            if limit > 0 and count >= limit:
                break

    def text_per_cpu_report(self, total_ns):
        print("### Per-CPU Usage ###")
        total_cpu_pc = 0
        nb_cpu = len(self.cpus.keys())
        for cpu in self.cpus.keys():
            cpu_total_ns = self.cpus[cpu].cpu_ns
            cpu_pc = self.cpus[cpu].cpu_pc
            total_cpu_pc += cpu_pc
            print("CPU %d : %d ns (%0.02f%%)" % (cpu, cpu_total_ns, cpu_pc))
        if nb_cpu == 0:
            return
        print("Total CPU Usage : %0.02f%%" % (total_cpu_pc / nb_cpu))
#        print(json.dumps(self.cpus, cls=CPUComplexEncoder))
