NSEC_PER_SEC = 1000000000
MSEC_PER_NSEC = 1000000

class Process():
    def __init__(self):
        self.tid = -1
        self.comm = ""
        self.cpu_ns = 0
        self.migrate_count = 0
        self.syscalls = {}
        pass

class CPU():
    def __init__(self):
        self.cpu_ns = 0
        self.current_tid = -1
        self.start_task_ns = 0
        pass

class Syscall():
    def __init__(self):
        self.name = ""
        self.count = 0
        pass

class Disk():
    def __init__(self):
        self.nr_sector = 0
        self.nr_requests = 0
        self.completed_requests = 0
        self.request_time = 0
        self.pending_requests = {}
        pass

class Iface():
    def __init__(self):
        self.recv_bytes = 0
        self.recv_packets = 0
        self.send_bytes = 0
        self.send_packets = 0
        pass

class FD():
    def __init__(self):
        pass
