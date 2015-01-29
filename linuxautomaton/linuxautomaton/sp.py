class StateProvider:
    def process_event(self, ev):
        raise NotImplementedError()

    def _register_cbs(self, cbs):
        self._cbs = cbs

    def _process_event_cb(self, ev):
        name = ev.name

        if name in self._cbs:
            self._cbs[name](ev)
        # for now we process all the syscalls at the same place
        if "syscall_entry" in self._cbs and \
                (name.startswith("sys_") or name.startswith("syscall_entry_")):
            self._cbs["syscall_entry"](ev)
        if "syscall_exit" in self._cbs and \
                (name.startswith("exit_syscall") or
                 name.startswith("syscall_exit_")):
            self._cbs["syscall_exit"](ev)
