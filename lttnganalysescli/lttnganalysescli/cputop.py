from .command import Command
import lttnganalyses.cputop
from linuxautomaton import common
from ascii_graph import Pyasciigraph
import operator


class Cputop(Command):
    _VERSION = '0.1.0'
    _DESC = """The cputop command."""

    def __init__(self):
        super().__init__(self._add_arguments, True)

    def _validate_transform_args(self):
        pass

    def run(self):
        # parse arguments first
        self._parse_args()
        # validate, transform and save specific arguments
        self._validate_transform_args()
        # open the trace
        self._open_trace()
        # create the appropriate analysis/analyses
        self._create_analysis()
        # run the analysis
        self._run_analysis(self._reset_total, self._refresh)
        # process the results
        self._compute_stats()
        # print results
        self._print_results(self.start_ns, self.trace_end_ts, final=1)
        # close the trace
        self._close_trace()

    def _create_analysis(self):
        self._analysis = lttnganalyses.cputop.Cputop(self._automaton.state)

    def _compute_stats(self):
        self.state = self._automaton.state
        for cpu in self.state.cpus.keys():
            current_cpu = self.state.cpus[cpu]
            total_ns = self.end_ns - self.start_ns
            if current_cpu.start_task_ns != 0:
                current_cpu.cpu_ns += self.end_ns - current_cpu.start_task_ns
            cpu_total_ns = current_cpu.cpu_ns
            current_cpu.cpu_pc = (cpu_total_ns * 100)/total_ns
            if current_cpu.current_tid >= 0:
                self.state.tids[current_cpu.current_tid].cpu_ns += \
                    self.end_ns - current_cpu.start_task_ns

    def _reset_total(self, start_ts):
        self.state = self._automaton.state
        for cpu in self.state.cpus.keys():
            current_cpu = self.state.cpus[cpu]
            current_cpu.cpu_ns = 0
            if current_cpu.start_task_ns != 0:
                current_cpu.start_task_ns = start_ts
            if current_cpu.current_tid >= 0:
                self.state.tids[current_cpu.current_tid].last_sched = start_ts
        for tid in self.state.tids.keys():
            self.state.tids[tid].cpu_ns = 0
            self.state.tids[tid].migrate_count = 0
            self.state.tids[tid].read = 0
            self.state.tids[tid].write = 0
            for syscall in self.state.tids[tid].syscalls.keys():
                self.state.tids[tid].syscalls[syscall].count = 0

    def _refresh(self, begin, end):
        self._compute_stats()
        self._print_results(begin, end, final=0)
        self._reset_total(end)

    def _print_results(self, begin_ns, end_ns, final=0):
#        print('event count: {}'.format(self._analysis.event_count))
        count = 0
        limit = self._arg_limit
        total_ns = end_ns - begin_ns
        graph = Pyasciigraph()
        values = []
        print('%s to %s' % (common.ns_to_asctime(begin_ns),
                            common.ns_to_asctime(end_ns)))
        for tid in sorted(self.state.tids.values(),
                          key=operator.attrgetter('cpu_ns'), reverse=True):
            if self._arg_proc_list and tid.comm not in self._arg_proc_list:
                continue
            pc = float("%0.02f" % ((tid.cpu_ns * 100) / total_ns))
            if tid.migrate_count > 0:
                migrations = ", %d migrations" % (tid.migrate_count)
            else:
                migrations = ""
            values.append(("%s (%d)%s" % (tid.comm, tid.tid, migrations), pc))
            count = count + 1
            if limit > 0 and count >= limit:
                break
        for line in graph.graph("Per-TID CPU Usage", values, unit=" %"):
            print(line)

        values = []
        total_cpu_pc = 0
        for cpu in sorted(self.state.cpus.values(),
                          key=operator.attrgetter('cpu_ns'), reverse=True):
            cpu_pc = float("%0.02f" % cpu.cpu_pc)
            total_cpu_pc += cpu_pc
            values.append(("CPU %d" % cpu.cpu_id, cpu_pc))
        for line in graph.graph("Per-CPU Usage", values, unit=" %"):
            print(line)
        print("\nTotal CPU Usage: %0.02f%%\n" %
              (total_cpu_pc / len(self.state.cpus.keys())))

    def _add_arguments(self, ap):
        # specific argument
        pass


# entry point
def run():
    # create command
    cputopcmd = Cputop()

    # execute command
    cputopcmd.run()
