import math

NSEC_PER_SEC = 1000000000
MSEC_PER_NSEC = 1000000

O_CLOEXEC = 0o2000000

class Process():
    def __init__(self):
        self.tid = -1
        self.pid = -1
        self.comm = ""
        self.cpu_ns = 0
        self.migrate_count = 0
        self.read = 0
        self.write = 0
        # indexed by syscall_name
        self.syscalls = {}
        # indexed by fd
        self.fds = {}
        # indexed by filename
        self.closed_fds = {}

class CPU():
    def __init__(self):
        self.cpu_ns = 0
        self.current_tid = -1
        self.start_task_ns = 0
        self.current_syscall = {}

class Syscall():
    def __init__(self):
        self.name = ""
        self.count = 0

class Disk():
    def __init__(self):
        self.nr_sector = 0
        self.nr_requests = 0
        self.completed_requests = 0
        self.request_time = 0
        self.pending_requests = {}

class Iface():
    def __init__(self):
        self.recv_bytes = 0
        self.recv_packets = 0
        self.send_bytes = 0
        self.send_packets = 0

class FD():
    def __init__(self):
        self.filename = ""
        self.fd = -1
        self.read = 0
        self.write = 0
        self.open = 0
        self.close = 0
        self.cloexec = 0
        # if FD was inherited, parent PID
        self.parent = -1

def get_disk(dev, disks):
    if not dev in disks:
        d = Disk()
        disks[dev] = d
    else:
        d = disks[dev]
    return d

def convert_size(size):
   if size <= 0:
       return "0B"
   size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
   i = int(math.floor(math.log(size,1024)))
   p = math.pow(1024,i)
   s = round(size/p,2)
   if (s > 0):
       return '%s %s' % (s,size_name[i])
   else:
       return '0B'
