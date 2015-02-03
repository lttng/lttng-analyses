# lttng-analyses

This repository contains various scripts to extract monitoring data and metrics
from LTTng kernel traces.

As opposed to other diagnostic or monitoring solutions, this approach is designed
to allow users to record their system's activity with a low overhead, wait
for a problem to occur and then diagnose its cause offline.

This solution allows the user to target hard to find problems and dig until the
root cause is found.

This README describes the implemented analyses as well as how to use them.

## Requirements
* LTTng >= 2.5
* Babeltrace >= 1.2 (with python bindings built)
* Python >= 3.4

## Install on Ubuntu (12.04 and 14.04 at least)
```bash
apt-get install -y software-properties-common (or python-software-properties on 12.04)
apt-add-repository -y ppa:lttng/ppa
apt-get update
apt-get -y install lttng-tools babeltrace lttng-modules-dkms python3-babeltrace python3-progressbar
```

```bash
git clone https://github.com/lttng/lttng-analyses.git
```

## Trace creation
Here are the basic commands to create a trace, for more information on the
LTTng setup, please refer to the [LTTng
documentation](http://lttng.org/docs/#doc-tracing-the-linux-kernel)

### Automatic
From the cloned git tree:
```bash
./lttng-analyses-record
```

### Manual
```bash
lttng create
lttng enable-channel -k bla --subbuf-size=4M
lttng enable-event -k sched_switch,block_rq_complete,block_rq_issue,block_bio_remap,block_bio_backmerge,netif_receive_skb,net_dev_xmit,sched_process_fork,sched_process_exec,lttng_statedump_process_state,lttng_statedump_file_descriptor,lttng_statedump_block_device,writeback_pages_written,mm_vmscan_wakeup_kswapd,mm_page_free,mm_page_alloc,block_dirty_buffer,irq_handler_entry,irq_handler_exit,softirq_entry,softirq_exit,softirq_raise -c bla
lttng enable-event -k --syscall -a -c bla
lttng start
..do stuff...
lttng stop
lttng destroy
```

### Remote trace creation
You can also create a trace on a server and send it to a remote host. The
remote host only needs to run `lttng-relayd -d` and be reachable over the network.
The only difference with the above commands is the tracing session's creation:
```bash
lttng create -U net://<remote-host>
```

## Implemented analyses

* CPU usage for the whole system
* CPU usage per-process
* Process CPU migration count
* Memory usage per-process (as seen by the kernel)
* Memory usage system-wide (as seen by the kernel)
* I/O usage (syscalls, disk, network)
* I/O operations log (with latency and usage)
* I/O latency statistics (open, read, write, sync operations)
* I/O latency frequency distribution
* Interrupt handler duration statistics (count, min, max, average stdev)
* Interrupt handler duration top
* Interrupt handler duration log
* Interrupt handler duration frequency distribution
* SoftIRQ handler latency statistics
* Syscalls usage statistics

All of the analyses share the same code architecture making it possible
to filter by timerange, process name, PID, min and max values using the
same command-line options. Also note that reported timestamps can
optionally be expressed in the GMT timezone to allow easy sharing between
teams.

The project's architecture makes it easy to add new analyses or to reuse
the analysis backend in external tools which may then present the results
in their own format (as opposed to text).

## Examples
After having collected your trace, any script contained in this repository
can be used to run an analysis. Read on for some examples!

### I/O
#### I/O latency stats
```bash
$ ./lttng-iolatencystats mytrace/
Timerange: [2015-01-06 10:58:26.140545481, 2015-01-06 10:58:27.229358936]
Syscalls latency statistics (usec):
Type                    Count            Min        Average            Max          Stdev
-----------------------------------------------------------------------------------------
Open                       45          5.562         13.835         77.683         15.263
Read                      109          0.316          5.774         62.569          9.277
Write                     101          0.256          7.060         48.531          8.555
Sync                      207         19.384         40.664        160.188         21.201

Disk latency statistics (usec):
Name                    Count            Min        Average            Max          Stdev
-----------------------------------------------------------------------------------------
dm-0                      108          0.001          0.004          0.007          1.306
```

#### I/O latency frequency distribution
```bash
$ ./lttng-iolatencyfreq mytrace/
Timerange: [2015-01-06 10:58:26.140545481, 2015-01-06 10:58:27.229358936]
Open latency distribution (usec)
###############################################################################
 5.562 ███████████████████████████████████████████████████████████████████  25
 9.168 ██████████                                                            4
12.774 █████████████████████                                                 8
16.380 ████████                                                              3
19.986 █████                                                                 2
23.592                                                                       0
27.198                                                                       0
30.804                                                                       0
34.410 ██                                                                    1
38.016                                                                       0
41.623                                                                       0
45.229                                                                       0
48.835                                                                       0
52.441                                                                       0
56.047                                                                       0
59.653                                                                       0
63.259                                                                       0
66.865                                                                       0
70.471                                                                       0
74.077 █████                                                                 2
```

#### I/O latency top
```bash
$ ./lttng-iolatencytop analysis-20150115-120942/ --limit 3 --minsize 2
Checking the trace for lost events...
Timerange: [2015-01-15 12:18:37.216484041, 2015-01-15 12:18:53.821580313]
Top open syscall latencies (usec)
Begin               End                  Name             Duration (usec)         Size  Proc                     PID      Filename      
[12:18:50.432950815,12:18:50.870648568]  open                  437697.753          N/A  apache2                  31517    /var/lib/php5/sess_0ifir2hangm8ggaljdphl9o5b5 (fd=13)
[12:18:52.946080165,12:18:52.946132278]  open                      52.113          N/A  apache2                  31588    /var/lib/php5/sess_mr9045p1k55vin1h0vg7rhgd63 (fd=13)
[12:18:46.800846035,12:18:46.800874916]  open                      28.881          N/A  apache2                  31591    /var/lib/php5/sess_r7c12pccfvjtas15g3j69u14h0 (fd=13)
[12:18:51.389797604,12:18:51.389824426]  open                      26.822          N/A  apache2                  31520    /var/lib/php5/sess_4sdb1rtjkhb78sabnoj8gpbl00 (fd=13)

Top read syscall latencies (usec)
Begin               End                  Name             Duration (usec)         Size  Proc                     PID      Filename      
[12:18:37.256073107,12:18:37.256555967]  read                     482.860       7.00 B  bash                     10237    unknown (origin not found) (fd=3)
[12:18:52.000209798,12:18:52.000252304]  read                      42.506      1.00 KB  irqbalance               1337     /proc/interrupts (fd=3)
[12:18:37.256559439,12:18:37.256601615]  read                      42.176       5.00 B  bash                     10237    unknown (origin not found) (fd=3)
[12:18:42.000281918,12:18:42.000320016]  read                      38.098      1.00 KB  irqbalance               1337     /proc/interrupts (fd=3)

Top write syscall latencies (usec)
Begin               End                  Name             Duration (usec)         Size  Proc                     PID      Filename      
[12:18:49.913241516,12:18:49.915908862]  write                   2667.346      95.00 B  apache2                  31584    /var/log/apache2/access.log (fd=8)
[12:18:37.472823631,12:18:37.472859836]  writev                    36.205     21.97 KB  apache2                  31544    unknown (origin not found) (fd=12)
[12:18:37.991578372,12:18:37.991612724]  writev                    34.352     21.97 KB  apache2                  31589    unknown (origin not found) (fd=12)
[12:18:39.547778549,12:18:39.547812515]  writev                    33.966     21.97 KB  apache2                  31584    unknown (origin not found) (fd=12)

Top sync syscall latencies (usec)
Begin               End                  Name             Duration (usec)         Size  Proc                     PID      Filename      
[12:18:50.162776739,12:18:51.157522361]  sync                  994745.622          N/A  sync                     22791    None (fd=None)
[12:18:37.227867532,12:18:37.232289687]  sync_file_range         4422.155          N/A  lttng-consumerd          19964    /home/julien/lttng-traces/analysis-20150115-120942/kernel/metadata (fd=32)
[12:18:37.238076585,12:18:37.239012027]  sync_file_range          935.442          N/A  lttng-consumerd          19964    /home/julien/lttng-traces/analysis-20150115-120942/kernel/metadata (fd=32)
[12:18:37.220974711,12:18:37.221647124]  sync_file_range          672.413          N/A  lttng-consumerd          19964    /home/julien/lttng-traces/analysis-20150115-120942/kernel/metadata (fd=32)
```

#### I/O operations log
```bash
$ ./lttng-iolog mytrace/
[10:58:26.221618530,10:58:26.221620659]  write                      2.129       8.00 B  /usr/bin/x-term          11793    anon_inode:[eventfd] (fd=5)
[10:58:26.221623609,10:58:26.221628055]  read                       4.446      50.00 B  /usr/bin/x-term          11793    /dev/ptmx (fd=24)
[10:58:26.221638929,10:58:26.221640008]  write                      1.079       8.00 B  /usr/bin/x-term          11793    anon_inode:[eventfd] (fd=5)
[10:58:26.221676232,10:58:26.221677385]  read                       1.153       8.00 B  /usr/bin/x-term          11793    anon_inode:[eventfd] (fd=5)
[10:58:26.223401804,10:58:26.223411683]  open                       9.879          N/A  sleep                    12420    /etc/ld.so.cache (fd=3)
[10:58:26.223448060,10:58:26.223455577]  open                       7.517          N/A  sleep                    12420    /lib/x86_64-linux-gnu/libc.so.6 (fd=3)
[10:58:26.223456522,10:58:26.223458898]  read                       2.376     832.00 B  sleep                    12420    /lib/x86_64-linux-gnu/libc.so.6 (fd=3)
[10:58:26.223918068,10:58:26.223929316]  open                      11.248          N/A  sleep                    12420     (fd=3)
[10:58:26.231881565,10:58:26.231895970]  writev                    14.405      16.00 B  /usr/bin/x-term          11793    socket:[45650] (fd=4)
[10:58:26.231979636,10:58:26.231988446]  recvmsg                    8.810      16.00 B  Xorg                     1827     socket:[47480] (fd=38)
```


#### I/O usage top
```bash
$ ./lttng-iousagetop traces/pgread-writes
Timerange: [2014-10-07 16:36:00.733214969, 2014-10-07 16:36:18.804584183]
Per-process I/O Read
###############################################################################
██████████████████████████████████████████████████    16.00 MB lttng-consumerd (2619)         0 B  file   4.00 B  net  16.00 MB unknown
█████                                                  1.72 MB lttng-consumerd (2619)         0 B  file      0 B  net   1.72 MB unknown
█                                                    398.13 KB postgres (4219)           121.05 KB file 277.07 KB net   8.00 B  unknown
                                                     256.09 KB postgres (1348)                0 B  file 255.97 KB net 117.00 B  unknown
                                                     204.81 KB postgres (4218)           204.81 KB file      0 B  net      0 B  unknown
                                                     123.77 KB postgres (4220)           117.50 KB file   6.26 KB net   8.00 B  unknown
Per-process I/O Write
###############################################################################
██████████████████████████████████████████████████    16.00 MB lttng-consumerd (2619)         0 B  file   8.00 MB net   8.00 MB unknown
██████                                                 2.20 MB postgres (4219)             2.00 MB file 202.23 KB net      0 B  unknown
█████                                                  1.73 MB lttng-consumerd (2619)         0 B  file 887.73 KB net 882.58 KB unknown
██                                                   726.33 KB postgres (1165)             8.00 KB file   6.33 KB net 712.00 KB unknown
                                                     158.69 KB postgres (1168)           158.69 KB file      0 B  net      0 B  unknown
                                                      80.66 KB postgres (1348)                0 B  file  80.66 KB net      0 B  unknown
Files Read
###############################################################################
██████████████████████████████████████████████████     8.00 MB anon_inode:[lttng_stream] (lttng-consumerd) 'fd 32 in lttng-consumerd (2619)'
█████                                                834.41 KB base/16384/pg_internal.init 'fd 7 in postgres (4219)', 'fd 7 in postgres (4220)', 'fd 7 in postgres (4221)', 'fd 7 in postgres (4222)', 'fd 7 in postgres (4223)', 'fd 7 in postgres (4224)', 'fd 7 in postgres (4225)', 'fd 7 in postgres (4226)'
█                                                    256.09 KB socket:[8893] (postgres) 'fd 9 in postgres (1348)'
█                                                    174.69 KB pg_stat_tmp/pgstat.stat 'fd 9 in postgres (4218)', 'fd 9 in postgres (1167)'
                                                     109.48 KB global/pg_internal.init 'fd 7 in postgres (4218)', 'fd 7 in postgres (4219)', 'fd 7 in postgres (4220)', 'fd 7 in postgres (4221)', 'fd 7 in postgres (4222)', 'fd 7 in postgres (4223)', 'fd 7 in postgres (4224)', 'fd 7 in postgres (4225)', 'fd 7 in postgres (4226)'
                                                     104.30 KB base/11951/pg_internal.init 'fd 7 in postgres (4218)'
                                                      12.85 KB socket (lttng-sessiond) 'fd 30 in lttng-sessiond (384)'
                                                       4.50 KB global/pg_filenode.map 'fd 7 in postgres (4218)', 'fd 7 in postgres (4219)', 'fd 7 in postgres (4220)', 'fd 7 in postgres (4221)', 'fd 7 in postgres (4222)', 'fd 7 in postgres (4223)', 'fd 7 in postgres (4224)', 'fd 7 in postgres (4225)', 'fd 7 in postgres (4226)'
                                                       4.16 KB socket (postgres) 'fd 9 in postgres (4226)'
                                                       4.00 KB /proc/interrupts 'fd 3 in irqbalance (1104)'
Files Write
###############################################################################
██████████████████████████████████████████████████     8.00 MB socket:[56371] (lttng-consumerd) 'fd 30 in lttng-consumerd (2619)'
█████████████████████████████████████████████████      8.00 MB pipe:[53306] (lttng-consumerd) 'fd 12 in lttng-consumerd (2619)'
██████████                                             1.76 MB pg_xlog/00000001000000000000000B 'fd 31 in postgres (4219)'
█████                                                887.82 KB socket:[56369] (lttng-consumerd) 'fd 26 in lttng-consumerd (2619)'
█████                                                882.58 KB pipe:[53309] (lttng-consumerd) 'fd 18 in lttng-consumerd (2619)'
                                                     160.00 KB /var/lib/postgresql/9.1/main/base/16384/16602 'fd 14 in postgres (1165)'
                                                     158.69 KB pg_stat_tmp/pgstat.tmp 'fd 3 in postgres (1168)'
                                                     144.00 KB /var/lib/postgresql/9.1/main/base/16384/16613 'fd 12 in postgres (1165)'
                                                      88.00 KB /var/lib/postgresql/9.1/main/base/16384/16609 'fd 11 in postgres (1165)'
                                                      78.28 KB socket:[8893] (postgres) 'fd 9 in postgres (1348)'
Block I/O Read
###############################################################################
Block I/O Write
###############################################################################
██████████████████████████████████████████████████     1.76 MB postgres (pid=4219)
████                                                 160.00 KB postgres (pid=1168)
██                                                   100.00 KB kworker/u8:0 (pid=1540)
██                                                    96.00 KB jbd2/vda1-8 (pid=257)
█                                                     40.00 KB postgres (pid=1166)
                                                       8.00 KB kworker/u9:0 (pid=4197)
                                                       4.00 KB kworker/u9:2 (pid=1381)
Disk nr_sector
###############################################################################
███████████████████████████████████████████████████████████████████  4416.00 sectors  vda1
Disk nr_requests
###############################################################################
████████████████████████████████████████████████████████████████████  177.00 requests  vda1
Disk request time/sector
###############################################################################
██████████████████████████████████████████████████████████████████   0.01 ms  vda1
Network recv_bytes
###############################################################################
███████████████████████████████████████████████████████  739.50 KB eth0
█████                                                    80.27 KB lo
Network sent_bytes
###############################################################################
████████████████████████████████████████████████████████  9.36 MB eth0
```

### IRQ
#### Handler duration and raise latency statistics
```bash
$ ./lttng-irqstats mytrace/
Timerange: [2014-03-11 16:05:41.314824752, 2014-03-11 16:05:45.041994298]
Hard IRQ                                             Duration (us)
                       count          min          avg          max        stdev
----------------------------------------------------------------------------------|
1:  <i8042>               30       10.901       45.500       64.510       18.447  |
42: <ahci>               259        3.203        7.863       21.426        3.183  |
43: <eth0>                 2        3.859        3.976        4.093        0.165  |
44: <iwlwifi>             92        0.300        3.995        6.542        2.181  |

Soft IRQ                                             Duration (us)                                        Raise latency (us)
                       count          min          avg          max        stdev  |  count          min          avg          max        stdev
----------------------------------------------------------------------------------|------------------------------------------------------------
1:  <TIMER_SOFTIRQ>      495        0.202       21.058       51.060       11.047  |     53        2.141       11.217       20.005        7.233
3:  <NET_RX_SOFTIRQ>      14        0.133        9.177       32.774       10.483  |     14        0.763        3.703       10.902        3.448
4:  <BLOCK_SOFTIRQ>      257        5.981       29.064      125.862       15.891  |    257        0.891        3.104       15.054        2.046
6:  <TASKLET_SOFTIRQ>     26        0.309        1.198        1.748        0.329  |     26        9.636       39.222       51.430       11.246
7:  <SCHED_SOFTIRQ>      299        1.185       14.768       90.465       15.992  |    298        1.286       31.387       61.700       11.866
9:  <RCU_SOFTIRQ>        338        0.592        3.387       13.745        1.356  |    147        2.480       29.299       64.453       14.286
```

#### Handler duration frequency distribution
```bash
$ ./lttng-irqfreq --timerange [16:05:42,16:05:45] --irq 44 --stats mytrace/
Timerange: [2014-03-11 16:05:42.042034570, 2014-03-11 16:05:44.998914297]
Hard IRQ                                             Duration (us)
                       count          min          avg          max        stdev
----------------------------------------------------------------------------------|
44: <iwlwifi>             72        0.300        4.018        6.542        2.164  |
Frequency distribution iwlwifi (44)
###############################################################################
0.300 █████                                                                 1.00
0.612 ██████████████████████████████████████████████████████████████        12.00
0.924 ████████████████████                                                  4.00
1.236 ██████████                                                            2.00
1.548                                                                       0.00
1.861 █████                                                                 1.00
2.173                                                                       0.00
2.485 █████                                                                 1.00
2.797 ██████████████████████████                                            5.00
3.109 █████                                                                 1.00
3.421 ███████████████                                                       3.00
3.733                                                                       0.00
4.045 █████                                                                 1.00
4.357 █████                                                                 1.00
4.669 ██████████                                                            2.00
4.981 ██████████                                                            2.00
5.294 █████████████████████████████████████████                             8.00
5.606 ████████████████████████████████████████████████████████████████████  13.00
5.918 ██████████████████████████████████████████████████████████████        12.00
6.230 ███████████████                                                       3.00
```

### Others
There are a lot of other scripts, we encourage you to try them and read the
```--help``` to see all the available options.

## Work in progress
Track the page cache and extract the latencies associated with pages flush to disk.
In order to do that, we rely on the assumption that the pages are flushed in a FIFO
order. It might not be 100% accurate, but it already gives great results :

An example here when saving a file in vim:
```
[19:57:51.173332284 - 19:57:51.177794657] vim (31517) syscall_entry_fsync(fd = 4 <blabla>) = 0, 4.462 ms
                                          1 dirty page(s) were flushed (assuming FIFO):
                                                vim (31517): 1 pages
                                                 - blabla : 1 pages
                                          13 active dirty filesystem page(s) (known):
                                                redis-server (2092): 2 pages
                                                 - /var/log/redis/redis-server.log : 2 pages
                                                vim (31517): 2 pages
                                                 - .blabla.swp : 2 pages
                                                lttng-consumerd (6750): 9 pages
                                                 - unknown (origin not found) : 9 pages
```

An other example when running the 'sync' command:
```
[19:57:53.046840755 - 19:57:53.072809609] sync (31554) syscall_entry_sync(fd =  <unknown>) = 0, 25.969 ms
                                          23 dirty page(s) were flushed (assuming FIFO):
                                                redis-server (2092): 2 pages
                                                 - /var/log/redis/redis-server.log : 2 pages
                                                vim (31517): 9 pages
                                                 - /home/julien/.viminfo.tmp : 6 pages
                                                 - .blabla.swp : 3 pages
                                                lttng-consumerd (6750): 12 pages
                                                 - unknown (origin not found) : 12 pages
```

PostgreSQL with 'sys_fdatasync':
```
[13:49:39.908599447 - 13:49:39.915930730] postgres (1137) sys_fdatasync(fd = 7 </var/lib/postgresql/9.1/main/pg_xlog/000000010000000000000008>) = 0, 7.331 ms
                                          2 pages allocated during the period
                                          88 dirty page(s) were flushed (assuming FIFO):
                                                postgres (1137): 88 pages
                                                 - /var/lib/postgresql/9.1/main/pg_xlog/000000010000000000000008 : 88 pages
                                          68 last dirtied filesystem page(s):
                                                postgres (2419): 68 pages
                                                 - base/11951/18410 : 46 pages
                                                 - base/11951/18407 : 10 pages
                                                 - base/11951/18407_fsm : 6 pages
                                                 - base/11951/18410_fsm : 6 pages
```

Detecting a fight for the I/O between a huge write and postgresql:
```
[13:49:47.242730583 - 13:49:47.442835037] python (2353) sys_write(fd = 3 </root/bla>, count = 102395904) = 102395904, 200.104 ms
                                          34760 pages allocated during the period
                                          woke up kswapd during the period
                                          10046 pages written on disk
                                          freed 33753 pages from the cache during the period
                                          1397 last dirtied filesystem page(s):
                                                python (2353): 1325 pages
                                                 - /root/bla : 1325 pages
                                                postgres (2419): 72 pages
                                                 - base/11951/18419 : 72 pages
```

## Limitations

The main limitation of this project is the fact that it can be quite slow to
process a large trace. This project is a work in progress and we focus on the
problem-solving aspect. Therefore, features have been prioritized over
performance for now.

One other aspect is the fact that the state is not persistent; the trace has
to be re-processed if another analysis script is to be used on the same trace.
Some scripts belonging to the same category allow the combination of multiple
analyses into a single pass (see ```--freq```, ```--log```, ```--usage```,
```--latencystats```, etc). We are planning to add a way to save the state
and/or create an interactive environment to allow the user to run multiple
analyses on the same trace without having to process the trace every time.


## Conclusion
We hope you have fun trying this project and please remember it is a work in
progress; feedback, bug reports and improvement ideas are always welcome!
