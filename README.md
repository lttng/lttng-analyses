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
request, so it is then easier to dig into the trace and understand why this
latency happened. It is also possible to see all the I/O requests performed by
a list of processes.

## Requirements
LTTng 2.5
Babeltrace 1.2 (with python bindings compiled)
Python 3

## Install on Ubuntu (12.04 and 14.04 at least)
```
# apt-get install -y software-properties-common (or python-software-properties on 12.04)
# apt-add-repository -y ppa:lttng/ppa
# apt-get update
# apt-get -y install lttng-tools babeltrace lttng-modules-dkms python3-babeltrace python3-progressbar
```

(If your user is part of the tracing group, you can avoid needing to be root
next, after a fresh install it requires to logout and login)

## Trace creation
```
# lttng create
# lttng enable-event -k sched_switch,block_rq_complete,block_rq_issue,block_bio_remap,block_bio_backmerge,netif_receive_skb,net_dev_xmit,sched_process_fork,sched_process_exec,lttng_statedump_process_state,lttng_statedump_file_descriptor,lttng_statedump_block_device
# lttng enable-event -k --syscall -a
# lttng start
...do stuff...
# lttng stop
# lttng destroy
```

## Remote Trace creation
You can also create a trace on a server and send it to a remote host. The
remote host only need to run `lttng-relayd -d` and be reachable by network.
The only difference with the above commands is the trace session creation `# lttng create -U net://<remote-host>`

## Run the analysis
Once you have collected your trace, you can run iotop.py on it.  In this
example, we want to extract all the I/O requests that took more than 100ms to
complete and also display the general statistics. The use-case in this example
was a rsync started while sysbench was running. We can clearly see that as soon
as rsync starts, it fights with sysbench for I/O ressources. Also in this
case, we see the lttng-consumerd daemon taking some I/O ressources to write the
trace on disk. To avoid this, write the trace on a separate disk or on the
network.

```
$ ./iotop.py --latency 100 /home/julien/lttng-traces/auto-20140717-131713/kernel/
[21:57:44.163759623 - 21:57:44.294381715] sysbench (22269) sys_read(fd = 3 <socket:[7234808]>, count = 16384) = 11, 130.622 ms
[21:57:45.191809562 - 21:57:45.301803269] sysbench (22269) sys_read(fd = 3 <socket:[7234808]>, count = 16384) = 11, 109.994 ms
[21:57:45.770038531 - 21:57:45.988275683] lttng-consumerd (9566) sys_splice(fd = 8 <pipe:[39694]>, count = 65536) = 65536, 218.237 ms
[21:57:45.979726386 - 21:57:46.083225973] sysbench (22269) sys_read(fd = 3 <socket:[7234808]>, count = 16384) = 11, 103.500 ms
[21:57:54.601077853 - 21:57:54.707630983] rsync (22313) sys_read(fd = 3 <usr/bin/elfedit>, count = 31488) = 31488, 106.553 ms
[21:57:54.587592973 - 21:57:54.719195920] sysbench (22269) sys_read(fd = 3 <socket:[7234808]>, count = 16384) = 11, 131.603 ms
[21:57:55.072895836 - 21:57:55.202645834] rsync (22313) sys_read(fd = 3 <usr/bin/euare-useraddloginprofile>, count = 176) = 176, 129.750 ms
[21:57:55.075782743 - 21:57:55.317097615] sysbench (22269) sys_read(fd = 3 <socket:[7234808]>, count = 16384) = 11, 241.315 ms
[21:57:55.294404884 - 21:57:55.442696225] rsync (22313) sys_read(fd = 3 <usr/bin/euare-usermodcert>, count = 194) = 194, 148.291 ms
[21:57:55.322062626 - 21:57:55.505492297] sysbench (22269) sys_read(fd = 3 <socket:[7234808]>, count = 16384) = 11, 183.430 ms
[21:57:56.265125208 - 21:57:56.421001530] sysbench (22269) sys_read(fd = 3 <socket:[7234808]>, count = 16384) = 11, 155.876 ms
[21:57:56.448781831 - 21:57:56.558016122] rsync (22313) sys_read(fd = 3 <usr/bin/getkeycodes>, count = 10488) = 10488, 109.234 ms
[21:57:56.425079318 - 21:57:56.615935358] sysbench (22269) sys_read(fd = 3 <socket:[7234808]>, count = 16384) = 11, 190.856 ms
[21:57:57.277529347 - 21:57:57.399115830] sysbench (22269) sys_read(fd = 3 <socket:[7234808]>, count = 16384) = 11, 121.586 ms
[21:57:57.403177716 - 21:57:57.508025924] sysbench (22269) sys_read(fd = 3 <socket:[7234808]>, count = 16384) = 11, 104.848 ms
[21:57:58.306824616 - 21:57:58.462797634] sysbench (22269) sys_read(fd = 3 <socket:[7234808]>, count = 16384) = 11, 155.973 ms
[21:58:00.212647591 - 21:58:00.320257030] sysbench (22269) sys_read(fd = 3 <socket:[7234808]>, count = 16384) = 11, 107.609 ms
[21:58:02.181064404 - 21:58:02.285614573] sysbench (22269) sys_read(fd = 3 <socket:[7234808]>, count = 16384) = 11, 104.550 ms
[21:58:02.289504854 - 21:58:02.402675415] sysbench (22269) sys_read(fd = 3 <socket:[7234808]>, count = 16384) = 11, 113.171 ms
[21:58:05.325260731 - 21:58:05.427694823] sysbench (22269) sys_read(fd = 3 <socket:[7234808]>, count = 16384) = 11, 102.434 ms
[21:58:05.431727970 - 21:58:05.541078397] sysbench (22269) sys_read(fd = 3 <socket:[7234808]>, count = 16384) = 11, 109.350 ms
[21:58:06.894296050 - 21:58:07.040442462] sysbench (22269) sys_read(fd = 3 <socket:[7234808]>, count = 16384) = 11, 146.146 ms
[21:57:40.630134783 - 21:58:08.451104062] exp2.sh (22307) sys_read(fd = 0 </dev/pts/2>, count = 128) = 1, 27820.969 ms
Wed May 14 21:57:40 2014 to Wed May 14 21:58:08 2014
Syscall I/O Read
###############################################################################################################################################
██████████████████████████████████████████████████  31141743  29.7 MB rsync (22313), 29.66 MB disk, 0 B net, 0 B block, 35.5 KB unknown        
█████████████████████████████████████████████████   30853205  29.42 MB rsync (22315), 3.71 KB disk, 0 B net, 0 B block, 29.42 MB unknown       
██████████████████████████████████                  21221788  20.24 MB lttng-consumerd (9561), 0 B disk, 0 B net, 0 B block, 20.24 MB unknown  
████████                                             5501782  5.25 MB sysbench (22267), 0 B disk, 0 B net, 0 B block, 5.25 MB unknown          
                                                      241413  235.75 KB mysqld (6048), 0 B disk, 0 B net, 0 B block, 235.75 KB unknown         
                                                      209196  204.29 KB lttng-consumerd (9565), 0 B disk, 0 B net, 0 B block, 204.29 KB unknown
                                                       55664  54.36 KB rsync (22314), 3.71 KB disk, 0 B net, 0 B block, 50.65 KB unknown       
                                                       13156  12.85 KB lttng-sessiond (9352), 0 B disk, 0 B net, 0 B block, 12.85 KB unknown   
                                                       10957  10.7 KB irqbalance (1460), 10.7 KB disk, 0 B net, 0 B block, 0 B unknown         
                                                        8824  8.62 KB lttng (22316), 8.62 KB disk, 0 B net, 0 B block, 0 B unknown             
Block I/O Read
###############################################################################
                                                        0  0 B init (1)        
                                                        0  0 B kthreadd (2)    
                                                        0  0 B ksoftirqd/0 (3) 
                                                        0  0 B kworker/0:0H (5)
                                                        0  0 B rcu_sched (7)   
                                                        0  0 B rcuos/0 (8)     
                                                        0  0 B rcuos/1 (9)     
                                                        0  0 B rcuos/2 (10)    
                                                        0  0 B rcuos/3 (11)    
                                                        0  0 B rcuos/4 (12)    
Syscall I/O Write
#############################################################################################################################################
██████████████████████████████████████████████████  30849641  29.42 MB rsync (22313), 0 B disk, 0 B net, 0 B block, 29.42 MB unknown         
█████████████████████████████████████████████████   30825835  29.4 MB rsync (22315), 29.35 MB disk, 0 B net, 0 B block, 50.6 KB unknown      
██████████████████████████████████                  21222108  20.24 MB lttng-consumerd (9561), 0 B disk, 0 B net, 0 B block, 20.24 MB unknown
████████                                             5501793  5.25 MB mysqld (6048), 0 B disk, 0 B net, 0 B block, 5.25 MB unknown           
                                                      241413  235.75 KB sysbench (22267), 0 B disk, 0 B net, 0 B block, 235.75 KB unknown    
                                                      209508  204.6 KB lttng-consumerd (9565), 0 B disk, 0 B net, 0 B block, 204.6 KB unknown
                                                       36355  35.5 KB rsync (22314), 0 B disk, 0 B net, 0 B block, 35.5 KB unknown           
                                                       21912  21.4 KB qemu-system-x86 (1996), 0 B disk, 0 B net, 0 B block, 21.4 KB unknown  
                                                        2152  2.1 KB qemu-system-x86 (2093), 0 B disk, 0 B net, 0 B block, 2.1 KB unknown    
                                                         398  398.0 B sshd (22132), 0 B disk, 0 B net, 0 B block, 398.0 B unknown            
Block I/O Write
###############################################################################
                                                        0  0 B init (1)        
                                                        0  0 B kthreadd (2)    
                                                        0  0 B ksoftirqd/0 (3) 
                                                        0  0 B kworker/0:0H (5)
                                                        0  0 B rcu_sched (7)   
                                                        0  0 B rcuos/0 (8)     
                                                        0  0 B rcuos/1 (9)     
                                                        0  0 B rcuos/2 (10)    
                                                        0  0 B rcuos/3 (11)    
                                                        0  0 B rcuos/4 (12)    
Files Read
#####################################################################################################################
██████████████████████████████████████████████████  30849402   29.42 MB (1 22314)                                    
                                                      230048  pipe:[39697] (lttng-consumerd) 224.66 KB (14 9561)     
                                                       88165  unknown (origin not found) 86.1 KB (43 9463)           
                                                        9288  anon_inode:[eventfd] (qemu-system-x86) 9.07 KB (4 2093)
                                                        2096  socket:[11618] (ovs-vswitchd) 2.05 KB (16 851)         
                                                        1404  /dev/net/tun 1.37 KB (23 2093)                         
                                                          72  socket:[7236711] (sshd) 72.0 B (3 22132)               
                                                          40  socket:[10756] (neutron-openvsw) 40.0 B (7 1369)       
                                                          16  /dev/urandom 16.0 B (5 1369)                           
                                                           1  /dev/pts/2 1.0 B (0 21985)                             
Disk nr_sector
###############################################################################
Disk nr_requests
###############################################################################
Disk request time/sector
###############################################################################
Network recv_bytes
###############################################################################
███████████████████████████████████████████████████████  409688  400.09 KB eth0
████████                                                  64546  63.03 KB vnet0
███████                                                   54468  53.19 KB vnet1
                                                            276  276.0 B virbr0
                                                              0  0 B vnet3     
                                                              0  0 B vnet2     
Network sent_bytes
###############################################################################
█████████████████████████████████████████████████████  12684026  12.1 MB eth0  
                                                          68908  67.29 KB vnet1
                                                          61682  60.24 KB vnet0
                                                           1722  1.68 KB virbr0
                                                            728  728.0 B vnet2 
                                                            676  676.0 B vnet3 
exp2.sh requests latency (ms)
####################################################################################
██████████████████████████████████████████████████  27820.969279  21:57:40.630134783
sysbench requests latency (ms)
##################################################################################
███████████████████████████                         130.622092  21:57:44.163759623
██████████████████████                              109.993707  21:57:45.191809562
█████████████████████                               103.499587  21:57:45.979726386
███████████████████████████                         131.602947  21:57:54.587592973
██████████████████████████████████████████████████  241.314872  21:57:55.075782743
██████████████████████████████████████              183.429671  21:57:55.322062626
████████████████████████████████                    155.876322  21:57:56.265125208
███████████████████████████████████████              190.85604  21:57:56.425079318
█████████████████████████                           121.586483  21:57:57.277529347
█████████████████████                               104.848208  21:57:57.403177716
████████████████████████████████                    155.973018  21:57:58.306824616
██████████████████████                              107.609439  21:58:00.212647591
█████████████████████                               104.550169  21:58:02.181064404
███████████████████████                             113.170561  21:58:02.289504854
█████████████████████                               102.434092  21:58:05.325260731
██████████████████████                              109.350427  21:58:05.431727970
██████████████████████████████                      146.146412  21:58:06.894296050
lttng-consumerd requests latency (ms)
##################################################################################
██████████████████████████████████████████████████  218.237152  21:57:45.770038531
rsync requests latency (ms)
##################################################################################
███████████████████████████████████                  106.55313  21:57:54.601077853
███████████████████████████████████████████         129.749998  21:57:55.072895836
██████████████████████████████████████████████████  148.291341  21:57:55.294404884
████████████████████████████████████                109.234291  21:57:56.448781831
```

This trace was collected before we had all the instrumentation required to extract
nicely all the block usage and resolve the name of the partitions, now it looks more like :
```
Disk nr_sector
###############################################################################
████████████████████████████████████████████████████████████████████  872  dm-0
██                                                                     32  sda2
Disk nr_requests
###############################################################################
█████████████████████████████████████████████████████████████████████  49  dm-0
██                                                                      2  sda2
Disk request time/sector
###############################################################################
███████████████████████████████████████████████████████████████  0.017  ms sda2
██████████████████                                               0.005  ms dm-0
```
