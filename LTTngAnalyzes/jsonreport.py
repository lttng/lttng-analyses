from LTTngAnalyzes.common import *
import operator
import json

class JsonReport():
    def __init__(self, trace_start_ts, trace_end_ts, cpus, tids):
        self.trace_start_ts = trace_start_ts
        self.trace_end_ts = trace_end_ts
        self.cpus = cpus
        self.tids = tids

    def json_per_cpu_report(self, start, end):
        out = {}
        out_per_cpu = {}
        out_ts = {"start" : int(start), "end" : int(end)}
        total_pc = 0
        for cpu in self.cpus.keys():
            out_per_cpu[cpu] = int(self.cpus[cpu].cpu_pc)
            total_pc += out_per_cpu[cpu]
        out["per-cpu"] = out_per_cpu
        out["timestamp"] = out_ts
        out["total-cpu"] = int(total_pc / len(self.cpus.keys()))
        print(json.dumps(out, indent=4))

    def json_per_tid_report(self, start, end, proc_list):
        out = {}
        out_per_tid = {}
        out_ts = {"start" : int(start), "end" : int(end)}
        total_ns = end - start
        for tid in self.tids.keys():
            if len(proc_list) > 0 and not self.tids[tid].comm in proc_list:
                continue
            proc = {}
            proc["procname"] = self.tids[tid].comm
            proc["percent"] = int((self.tids[tid].cpu_ns * 100)/ total_ns)
            out_per_tid[tid] = proc
        out["per-tid"] = out_per_tid
        out["timestamp"] = out_ts
        print(json.dumps(out, indent=4))

    def json_global_per_cpu_report(self):
        a = []
        for cpu in self.cpus.keys():
            b = {}
            b["key"] = "CPU %d" % cpu
            b["values"] = self.cpus[cpu].total_per_cpu_pc_list
            a.append(b)
        print(json.dumps(a))

    def json_trace_info(self):
        out = {}
        total_ns = self.trace_end_ts - self.trace_start_ts
        out["start"] = self.trace_start_ts
        out["end"] = self.trace_end_ts
        out["total_ns"] = total_ns
        out["total_sec"] = "%lu.%0.09lus" % ((total_ns / NSEC_PER_SEC,
                        total_ns % NSEC_PER_SEC))
        print(json.dumps(out, indent=4))

    def report(self, begin_ns, end_ns, final, args):
        if not (args.info or args.cpu or args.tid or args.overall):
            return
        if args.info and final:
            self.json_trace_info()
        if args.cpu:
            self.json_per_cpu_report(begin_ns, end_ns)
        if args.tid:
            self.json_per_tid_report(begin_ns, end_ns, args.display_proc_list)
        if args.overall and final:
            self.json_global_per_cpu_report()
