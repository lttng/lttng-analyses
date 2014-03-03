from LTTngAnalyzes.common import *
import operator

#class CPUComplexEncoder(json.JSONEncoder):
#    def default(self, obj):
#        if isinstance(obj, CPU):
#            return obj.cpu_pc
#        # Let the base class default method raise the TypeError
#        return json.JSONEncoder.default(self, obj)

class TextReport():
    def __init__(self, trace_start_ts, trace_end_ts, cpus, tids):
        self.trace_start_ts = trace_start_ts
        self.trace_end_ts = trace_end_ts
        self.cpus = cpus
        self.tids = tids

    def text_trace_info(self):
        total_ns = self.trace_end_ts - self.trace_start_ts
        print("### Trace info ###")
        print("Start : %lu\nEnd: %lu" % (self.trace_start_ts, self.trace_end_ts))
        print("Total ns : %lu" % (total_ns))
        print("Total : %lu.%0.09lus" % (total_ns / NSEC_PER_SEC,
            total_ns % NSEC_PER_SEC))

    def report(self, begin_ns, end_ns, final, args):
        if not (args.info or args.cpu or args.tid):
            return
        if args.cpu or args.tid:
            print("[%lu:%lu]" % (begin_ns/NSEC_PER_SEC, end_ns/NSEC_PER_SEC))

        total_ns = end_ns - begin_ns

        if args.info and final:
            self.text_trace_info()
        if args.cpu:
            self.text_per_cpu_report(total_ns)
        if args.tid:
            self.text_per_tid_report(total_ns, args.display_proc_list, limit=args.top)

    def text_per_tid_report(self, total_ns, proc_list, limit=0):
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
        print("Total CPU Usage : %0.02f%%" % (total_cpu_pc / nb_cpu))
#        print(json.dumps(self.cpus, cls=CPUComplexEncoder))
