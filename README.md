# lttng-analyses

This repository contains various scripts to extract monitoring data and metrics
from LTTng kernel traces.

This README only describes the usage for iotop.py, but the procedure is pretty-much
the same for the other scripts.

`iotop.py` displays the I/O usage in the trace, per-disk, per-network interface,
per-FD and per-process. It tracks the number of bytes and requests performed
and the latency of the I/O syscalls and block devices.

The user can specify a threshold to see the requests that took more than a
certain time to complete, this extracts the timestamp begin and end of the
requests, so it is then easier to dig into the trace and understand why this
latency happened. It is also possible to see all the I/O requests performed by
a list of processes (see `--name` parameter).

## Requirements
* LTTng 2.5
* Babeltrace 1.2 (with python bindings compiled)
* Python 3.4+

## Install on Ubuntu (12.04 and 14.04 at least)
```
apt-get install -y software-properties-common (or python-software-properties on 12.04)
apt-add-repository -y ppa:lttng/ppa
apt-get update
apt-get -y install lttng-tools babeltrace lttng-modules-dkms python3-babeltrace python3-progressbar
```

(If your user is part of the tracing group, you can avoid needing to be root
next, after a fresh install it requires to logout and login)

## Trace creation
```
lttng create
lttng enable-channel -k bla --subbuf-size=4M
lttng enable-event -k sched_switch,block_rq_complete,block_rq_issue,block_bio_remap,block_bio_backmerge,netif_receive_skb,net_dev_xmit,sched_process_fork,sched_process_exec,lttng_statedump_process_state,lttng_statedump_file_descriptor,lttng_statedump_block_device,writeback_pages_written,mm_vmscan_wakeup_kswapd,mm_page_free,mm_page_alloc,block_dirty_buffer -c bla
lttng enable-event -k --syscall -a -c bla
lttng start
..do stuff...
lttng stop
lttng destroy
```

## Remote trace creation
You can also create a trace on a server and send it to a remote host. The
remote host only need to run `lttng-relayd -d` and be reachable by network.
The only difference with the above commands is the trace session creation :
```
lttng create -U net://<remote-host>
```

## Run the analysis
Once you have collected your trace, you can run iotop.py on it. In this
example, we want to extract all the I/O requests that took more than 50ms to
complete and also display the general statistics. The use-case in this example
is concurrent read and writes in a postgresql database. Here is some extracts
from the output of the script :

```
./iotop.py --no-progress --latency 50  /home/julien/lttng-traces/reddit-postgres01/pgread-writes/kernel/ 
[16:36:02.916132296 - 16:36:02.994389303] postgres (1348) syscall_entry_recvfrom(fd = 9 <socket:[8893]>, count = 5) = 5, 78.257 ms
[16:36:03.007633298 - 16:36:03.091402482] postgres (1348) syscall_entry_recvfrom(fd = 9 <socket:[8893]>, count = 5) = 5, 83.769 ms
[16:36:03.107392794 - 16:36:03.200894697] postgres (1348) syscall_entry_recvfrom(fd = 9 <socket:[8893]>, count = 5) = 5, 93.502 ms
[...]
[16:36:09.580490482 - 16:36:09.897385130] postgres (4219) syscall_entry_recvfrom(fd = 9 <socket>, count = 5) = 5, 316.895 ms
                                          2715 pages allocated during the period
[16:36:09.614727970 - 16:36:09.914140692] postgres (4220) syscall_entry_recvfrom(fd = 9 <socket>, count = 5) = 5, 299.413 ms
                                          2396 pages allocated during the period
[16:36:09.750251458 - 16:36:09.950608296] postgres (4224) syscall_entry_recvfrom(fd = 9 <socket>, count = 5) = 5, 200.357 ms
                                          904 pages allocated during the period
[...]
[16:36:06.783206662 - 16:36:11.748147198] postgres (1348) syscall_entry_recvfrom(fd = 9 <socket:[8893]>, count = 5) = 5, 4964.941 ms
                                          3541 pages allocated during the period
Tue Oct  7 16:36:00 2014 to Tue Oct  7 16:36:18 2014
Syscall I/O Read
################################################################################################################################################
██████████████████████████████████████████████████  16777220  16.0 MB lttng-consumerd (2619), 0 B disk, 4.0 B net, 0 B block, 16.0 MB unknown   
█████                                                1804880  1.72 MB lttng-consumerd (2623), 0 B disk, 0 B net, 0 B block, 1.72 MB unknown     
█                                                     407686  398.13 KB postgres (4219), 121.05 KB disk, 277.07 KB net, 0 B block, 8.0 B unknown
                                                      262235  256.09 KB postgres (1348), 0 B disk, 255.97 KB net, 0 B block, 117.0 B unknown    
                                                      209730  204.81 KB postgres (4218), 204.81 KB disk, 0 B net, 0 B block, 0 B unknown        
                                                      126737  123.77 KB postgres (4220), 117.5 KB disk, 6.26 KB net, 0 B block, 8.0 B unknown   
                                                      124579  121.66 KB postgres (4226), 117.5 KB disk, 4.15 KB net, 0 B block, 8.0 B unknown   
                                                      124189  121.28 KB postgres (4221), 117.5 KB disk, 3.77 KB net, 0 B block, 8.0 B unknown   
                                                      124125  121.22 KB postgres (4222), 117.5 KB disk, 3.71 KB net, 0 B block, 8.0 B unknown   
                                                      124125  121.22 KB postgres (4224), 117.5 KB disk, 3.71 KB net, 0 B block, 8.0 B unknown   
Syscall I/O Write
###################################################################################################################################################
██████████████████████████████████████████████████  16777336  16.0 MB lttng-consumerd (2619), 0 B disk, 8.0 MB net, 0 B block, 8.0 MB unknown      
██████                                               2304240  2.2 MB postgres (4219), 2.0 MB disk, 202.23 KB net, 1.76 MB block, 0 B unknown       
█████                                                1812800  1.73 MB lttng-consumerd (2623), 0 B disk, 887.73 KB net, 0 B block, 882.58 KB unknown
██                                                    743760  726.33 KB postgres (1165), 8.0 KB disk, 6.33 KB net, 0 B block, 712.0 KB unknown     
                                                      162500  158.69 KB postgres (1168), 158.69 KB disk, 0 B net, 160.0 KB block, 0 B unknown      
                                                       82592  80.66 KB postgres (1348), 0 B disk, 80.66 KB net, 0 B block, 0 B unknown             
                                                       40960  40.0 KB postgres (1166), 0 B disk, 0 B net, 40.0 KB block, 40.0 KB unknown           
                                                       13156  12.85 KB lttng (4227), 12.85 KB disk, 0 B net, 0 B block, 0 B unknown                
                                                       12256  11.97 KB postgres (4220), 2.0 B disk, 11.97 KB net, 0 B block, 0 B unknown           
                                                       10450  10.21 KB postgres (4226), 2.0 B disk, 10.2 KB net, 0 B block, 0 B unknown            
Block I/O Read
###############################################################################
                                                        0  0 B init (1)        
                                                        0  0 B kthreadd (2)    
                                                        0  0 B ksoftirqd/0 (3) 
                                                        0  0 B kworker/0:0 (4) 
                                                        0  0 B kworker/0:0H (5)
                                                        0  0 B rcu_sched (7)   
                                                        0  0 B rcuos/0 (8)     
                                                        0  0 B rcuos/1 (9)     
                                                        0  0 B rcuos/2 (10)    
                                                        0  0 B rcuos/3 (11)    
Block I/O Write
#########################################################################################
██████████████████████████████████████████████████  1843200  1.76 MB postgres (4219)     
████                                                 163840  160.0 KB postgres (1168)    
██                                                   102400  100.0 KB kworker/u8:0 (1540)
██                                                    98304  96.0 KB jbd2/vda1-8 (257)   
█                                                     40960  40.0 KB postgres (1166)     
                                                       8192  8.0 KB kworker/u9:0 (4197)  
                                                       4096  4.0 KB kworker/u9:2 (1381)  
                                                          0  0 B init (1)                
                                                          0  0 B kthreadd (2)            
                                                          0  0 B ksoftirqd/0 (3)         
Files Read
##########################################################################################################################
██████████████████████████████████████████████████  9289728  anon_inode:[lttng_stream] (lttng-consumerd) 8.86 MB (31 2619)
█████████████████████████████████████████████       8388608  pipe:[53306] (lttng-consumerd) 8.0 MB (11 2619)              
████                                                 903760  pipe:[53309] (lttng-consumerd) 882.58 KB (17 2619)           
█                                                    325340  socket (postgres) 317.71 KB (9 4219)                         
█                                                    262235  socket:[8893] (postgres) 256.09 KB (9 1348)                  
                                                      76600  socket:[10713] (postgres) 74.8 KB (8 4218)                   
                                                         52  /dev/ptmx 52.0 B (17 1)                                      
                                                         48  socket:[54589] (sshd) 48.0 B (3 3329)                        
                                                         32  /root/trace2.sh 32.0 B (255 4211)                            
                                                          1  /dev/pts/1 1.0 B (0 4211)                                    
Files Write
###########################################################################################################################
██████████████████████████████████████████████████  9289728  anon_inode:[lttng_stream] (lttng-consumerd) 8.86 MB (31 2619) 
█████████████████████████████████████████████       8388608  pipe:[53306] (lttng-consumerd) 8.0 MB (11 2619)               
████                                                 903760  pipe:[53309] (lttng-consumerd) 882.58 KB (17 2619)            
█                                                    325340  socket (postgres) 317.71 KB (9 4219)                          
█                                                    262235  socket:[8893] (postgres) 256.09 KB (9 1348)                   
                                                      76600  socket:[10713] (postgres) 74.8 KB (8 4218)                    
                                                      65536  /var/lib/postgresql/9.1/main/base/16384/16611 64.0 KB (9 1165)
                                                         52  /dev/ptmx 52.0 B (17 1)                                       
                                                         48  socket:[54589] (sshd) 48.0 B (3 3329)                         
                                                         32  /root/trace2.sh 32.0 B (255 4211)                             
                                                          1  /dev/pts/1 1.0 B (0 4211)                                     
Disk nr_sector
###############################################################################
███████████████████████████████████████████████████████████████████  4416  vda1
Disk nr_requests
###############################################################################
████████████████████████████████████████████████████████████████████  177  vda1
Disk request time/sector
###############################################################################
███████████████████████████████████████████████████████████████  0.014  ms vda1
                                                                   0.0  ms 0   
Network recv_bytes
###############################################################################
████████████████████████████████████████████████████████  757250  739.5 KB eth0
██████                                                     82200  80.27 KB lo  
Network sent_bytes
###############################################################################
████████████████████████████████████████████████████████  9811620  9.36 MB eth0
                                                            85000  83.01 KB lo 
trace2.sh requests latency (ms)
####################################################################################
██████████████████████████████████████████████████  18011.544456  16:36:00.788362068
postgres requests latency (ms)
###################################################################################
                                                      78.257007  16:36:02.916132296
                                                      83.769184  16:36:03.007633298
                                                      93.501903  16:36:03.107392794
[...]
███                                                  316.894648  16:36:09.580490482
███                                                  299.412722  16:36:09.614727970
██                                                   200.356838  16:36:09.750251458
[...]
██████████████████████████████████████████████████  4964.940536  16:36:06.783206662
```

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

Postgresql with 'sys_fdatasync':
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

## Conclusion
Hope you have fun trying it and please remember it is a work in progress, feedbacks, bug reports and ideas are alway welcome !
