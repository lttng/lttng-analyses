from .sched import SchedStateProvider
from .mem import MemStateProvider
from .irq import IrqStateProvider
from .syscalls import SyscallsStateProvider
from .statedump import StatedumpStateProvider
from .block import BlockStateProvider
from .net import NetStateProvider


class State:
    def __init__(self):
        self.cpus = {}
        self.tids = {}
        self.disks = {}
        self.syscalls = {}
        self.mm = {}
        self.ifaces = {}
        self.dirty_pages = {}
        self.interrupts = {}
        self.pending_syscalls = []


class Automaton:
    def __init__(self):
        self._state = State()
        self._state_providers = [
            SchedStateProvider(self._state),
            MemStateProvider(self._state),
            IrqStateProvider(self._state),
            SyscallsStateProvider(self._state),
            StatedumpStateProvider(self._state),
            BlockStateProvider(self._state),
            NetStateProvider(self._state),
        ]

    def process_event(self, ev):
        for sp in self._state_providers:
            sp.process_event(ev)

    @property
    def state(self):
        return self._state
