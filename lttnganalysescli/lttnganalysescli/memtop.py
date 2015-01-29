from .command import Command
import lttnganalyses.memtop
from linuxautomaton import common
from ascii_graph import Pyasciigraph
import operator


class Memtop(Command):
    _VERSION = '0.1.0'
    _DESC = """The memtop command."""

    def __init__(self):
        super().__init__(self._add_arguments, enable_proc_filter_args=True)

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
        self._analysis = lttnganalyses.memtop.Memtop(self._automaton.state)

    def _compute_stats(self):
        pass

    def _reset_total(self, start_ts):
        self.state = self._automaton.state
        for tid in self.state.tids.keys():
            self.state.tids[tid].allocated_pages = 0
            self.state.tids[tid].freed_pages = 0
        self.state.mm["allocated_pages"] = 0
        self.state.mm["freed_pages"] = 0
        self.state = self._automaton.state

    def _refresh(self, begin, end):
        self._compute_stats()
        self._print_results(begin, end, final=0)
        self._reset_total(end)

    def filter_process(self, proc):
        if self._arg_proc_list and proc.comm not in self._arg_proc_list:
            return False
        if self._arg_pid_list and str(proc.pid) not in self._arg_pid_list:
            return False
        return True

    def _print_results(self, begin_ns, end_ns, final=0):
        count = 0
        limit = self._arg_limit
        graph = Pyasciigraph()
        values = []
        self.state = self._automaton.state
        alloc = 0
        freed = 0
        print('%s to %s' % (common.ns_to_asctime(begin_ns),
                            common.ns_to_asctime(end_ns)))
        for tid in sorted(self.state.tids.values(),
                          key=operator.attrgetter('allocated_pages'),
                          reverse=True):
            if not self.filter_process(tid):
                continue
            values.append(("%s (%d)" % (tid.comm, tid.tid),
                          tid.allocated_pages))
            count = count + 1
            if limit > 0 and count >= limit:
                break
        for line in graph.graph("Per-TID Memory Allocations", values,
                                unit=" pages"):
            print(line)

        values = []
        count = 0
        for tid in sorted(self.state.tids.values(),
                          key=operator.attrgetter('freed_pages'),
                          reverse=True):
            if not self.filter_process(tid):
                continue
            values.append(("%s (%d)" % (tid.comm, tid.tid), tid.freed_pages))
            count = count + 1
            freed += tid.freed_pages
            if limit > 0 and count >= limit:
                break
        for line in graph.graph("Per-TID Memory Deallocation", values,
                                unit=" pages"):
            print(line)

        for tid in sorted(self.state.tids.values(),
                          key=operator.attrgetter('allocated_pages'),
                          reverse=True):
            if not self.filter_process(tid):
                continue
            alloc += tid.allocated_pages
        for tid in sorted(self.state.tids.values(),
                          key=operator.attrgetter('freed_pages'),
                          reverse=True):
            if not self.filter_process(tid):
                continue
            freed += tid.freed_pages
        print("\nTotal memory usage:\n- %d pages allocated\n- %d pages freed" %
             (alloc, freed))

    def _add_arguments(self, ap):
        # specific argument
        pass


# entry point
def run():
    # create command
    memtopcmd = Memtop()

    # execute command
    memtopcmd.run()
