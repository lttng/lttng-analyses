LTTng analyses
**************

.. image:: https://img.shields.io/pypi/v/lttnganalyses.svg?label=Latest%20version
   :target: https://pypi.python.org/pypi/lttnganalyses
   :alt: Latest version released on PyPi

.. image:: https://travis-ci.org/lttng/lttng-analyses.svg?branch=master&label=Travis%20CI%20build
   :target: https://travis-ci.org/lttng/lttng-analyses
   :alt: Status of Travis CI

.. image:: https://img.shields.io/jenkins/s/https/ci.lttng.org/lttng-analyses_master_build.svg?label=LTTng%20CI%20build
   :target: https://ci.lttng.org/job/barectf
   :alt: Status of LTTng CI

The **LTTng analyses** are a set of various executable analyses to
extract and visualize monitoring data and metrics from
`LTTng <http://lttng.org/>`_ kernel traces on the command line.

As opposed to other "live" diagnostic or monitoring solutions, this
approach is based on the following workflow:

#. Record your system's activity with LTTng, a low-overhead tracer.
#. Do whatever it takes for your problem to occur.
#. Diagnose your problem's cause **offline** (when tracing is stopped).

This solution allows you to target problems that are hard to find and
to "dig" until the root cause is found.

.. contents::
   :local:
   :depth: 2
   :backlinks: none


Install LTTng analyses
======================

.. NOTE::

   The version 2.0 of `Trace Compass <http://tracecompass.org/>`_
   requires LTTng analyses 0.4: Trace Compass 2.0 is not compatible
   with LTTng analyses 0.5 and after.

   In this case, we suggest that you install LTTng analyses from the
   ``stable-0.4`` branch of the project's Git repository (see
   `Install from the Git repository`_). You can also
   `download <https://github.com/lttng/lttng-analyses/releases>`_ the
   latest 0.4 release tarball and follow the
   `Install from a release tarball`_ procedure.


Required dependencies
---------------------

- `Python <https://www.python.org/>`_ ≥ 3.4
- `setuptools <https://pypi.python.org/pypi/setuptools>`_
- `Babeltrace <http://diamon.org/babeltrace/>`_ ≥ 1.2 with Python
  bindings (``--enable-python-bindings`` when building from source)


Optional dependencies
---------------------

- `LTTng <http://lttng.org/>`_ ≥ 2.5: to use the
  ``lttng-analyses-record`` script and to trace the system in
  general
- `termcolor <https://pypi.python.org/pypi/termcolor/>`_: color
  support
- `progressbar <https://pypi.python.org/pypi/progressbar/>`_:
  terminal progress bar support (this is not required for the
  machine interface's progress indication feature)


Install from PyPI (online repository)
-------------------------------------

To install the latest LTTng analyses release on your system from
`PyPI <https://pypi.python.org/pypi/lttnganalyses>`_:

#. Install the required dependencies.
#. **Optional**: Install the optional dependencies.
#. Make sure ``pip`` for Python 3 is installed on your system. The
   package is named ``python3-pip`` on most distributions
   (``python-pip`` on Arch Linux).
#. Use ``pip3`` to install LTTng analyses:

   .. code-block:: bash

      sudo pip3 install --upgrade lttnganalyses


Install from a release tarball
------------------------------

To install a specific LTTng analyses release (tarball) on your system:

#. Install the required dependencies.
#. **Optional**: Install the optional dependencies.
#. `Download <https://github.com/lttng/lttng-analyses/releases>`_ and
   extract the desired release tarball.
#. Use ``setup.py`` to install LTTng analyses:

   .. code-block:: bash

      sudo ./setup.py install


Install from the Git repository
-------------------------------

To install LTTng analyses from a specific branch or tag of the
project's Git repository:

#. Install the required dependencies.
#. **Optional**: Install the optional dependencies.
#. Make sure ``pip`` for Python 3 is installed on your system. The
   package is named ``python3-pip`` on most distributions
   (``python-pip`` on Arch Linux).
#. Use ``pip3`` to install LTTng analyses:

   .. code-block:: bash

      sudo pip3 install git+git://github.com/lttng/lttng-analyses.git@master

   Replace ``master`` with the desired branch or tag name to install
   in the previous URL.


Install on Ubuntu
-----------------

To install LTTng analyses on Ubuntu ≥ 12.04:

#. Add the *LTTng Latest Stable* PPA repository:

   .. code-block:: bash

      sudo apt-get install -y software-properties-common
      sudo apt-add-repository -y ppa:lttng/ppa
      sudo apt-get update

   Replace ``software-properties-common`` with
   ``python-software-properties`` on Ubuntu 12.04.
#. Install the required dependencies:

   .. code-block:: bash

      sudo apt-get install -y babeltrace
      sudo apt-get install -y python3-babeltrace
      sudo apt-get install -y python3-setuptools
#. **Optional**: Install the optional dependencies:

   .. code-block:: bash

      sudo apt-get install -y lttng-tools
      sudo apt-get install -y lttng-modules-dkms
      sudo apt-get install -y python3-progressbar
      sudo apt-get install -y python3-termcolor
#. Install LTTng analyses:

   .. code-block:: bash

      sudo apt-get install -y python3-lttnganalyses


Install on Debian "sid"
-----------------------

To install LTTng analyses on Debian "sid":

#. Install the required dependencies:

   .. code-block:: bash

      sudo apt-get install -y babeltrace
      sudo apt-get install -y python3-babeltrace
      sudo apt-get install -y python3-setuptools
#. **Optional**: Install the optional dependencies:

   .. code-block:: bash

      sudo apt-get install -y lttng-tools
      sudo apt-get install -y lttng-modules-dkms
      sudo apt-get install -y python3-progressbar
      sudo apt-get install -y python3-termcolor
#. Install LTTng analyses:

   .. code-block:: bash

      sudo apt-get install -y python3-lttnganalyses


Record a trace
==============

This section is a quick reminder of how to record an LTTng kernel
trace. See LTTng's `quick start guide
<http://lttng.org/docs/v2.7/#doc-getting-started>`_ to familiarize
with LTTng.


Automatic
---------

LTTng analyses ships with a handy (installed) script,
``lttng-analyses-record``, which automates
the steps to record a kernel trace with the events required by the
analyses.

To use ``lttng-analyses-record``:

#. Launch the script:

   .. code-block:: bash

      lttng-analyses-record
#. Do whatever it takes for your problem to occur.
#. When you are done recording, press Ctrl+C where the script is
   running.


Manual
------

To record an LTTng kernel trace suitable for the LTTng analyses:

#. Create a tracing session:

   .. code-block:: bash

      sudo lttng create
#. Create a channel with a large sub-buffer size:

   .. code-block:: bash

      sudo lttng enable-channel --kernel chan --subbuf-size=8M
#. Create event rules to capture the needed events:

   .. code-block:: bash

      sudo lttng enable-event --kernel --channel=chan block_bio_backmerge
      sudo lttng enable-event --kernel --channel=chan block_bio_remap
      sudo lttng enable-event --kernel --channel=chan block_dirty_buffer
      sudo lttng enable-event --kernel --channel=chan block_rq_complete
      sudo lttng enable-event --kernel --channel=chan block_rq_issue
      sudo lttng enable-event --kernel --channel=chan irq_handler_entry
      sudo lttng enable-event --kernel --channel=chan irq_handler_exit
      sudo lttng enable-event --kernel --channel=chan lttng_statedump_block_device
      sudo lttng enable-event --kernel --channel=chan lttng_statedump_file_descriptor
      sudo lttng enable-event --kernel --channel=chan lttng_statedump_process_state
      sudo lttng enable-event --kernel --channel=chan mm_page_alloc
      sudo lttng enable-event --kernel --channel=chan mm_page_free
      sudo lttng enable-event --kernel --channel=chan mm_vmscan_wakeup_kswapd
      sudo lttng enable-event --kernel --channel=chan net_dev_xmit
      sudo lttng enable-event --kernel --channel=chan netif_receive_skb
      sudo lttng enable-event --kernel --channel=chan sched_process_exec
      sudo lttng enable-event --kernel --channel=chan sched_process_fork
      sudo lttng enable-event --kernel --channel=chan sched_switch
      sudo lttng enable-event --kernel --channel=chan softirq_entry
      sudo lttng enable-event --kernel --channel=chan softirq_exit
      sudo lttng enable-event --kernel --channel=chan softirq_raise
      sudo lttng enable-event --kernel --channel=chan writeback_pages_written
      sudo lttng enable-event --kernel --channel=chan --syscall --all
#. Start recording:

   .. code-block:: bash

      sudo lttng start
#. Do whatever it takes for your problem to occur.
#. Stop recording and destroy the tracing session to free its
   resources:

   .. code-block:: bash

      sudo lttng stop
      sudo lttng destroy


See the `LTTng Documentation <http://lttng.org/docs/>`_ for other
use cases, like sending the trace data over the network instead of
recording trace files on the target's file system.


Analyze
=======

The **LTTng analyses** are a set of various command-line
analyses. Each analysis accepts the path to a recorded trace
(see `Record a trace`_) as its argument, as well as various command-line
options to control the analysis and its output.

Many command-line options are common to all the analyses, so that you
can filter by timerange, process name, process ID, minimum and maximum
values, and the rest. Also note that the reported timestamps can
optionally be expressed in the GMT time zone.

Each analysis is installed as an executable starting with the
``lttng-`` prefix.

.. list-table:: Available LTTng analyses
   :header-rows: 1

   * - Command
     - Description
   * - ``lttng-cputop``
     - Per-TID, per-CPU, and total top CPU usage.
   * - ``lttng-iolatencyfreq``
     - I/O request latency distribution.
   * - ``lttng-iolatencystats``
     - Partition and system call latency statistics.
   * - ``lttng-iolatencytop``
     - Top system call latencies.
   * - ``lttng-iolog``
     - I/O operations log.
   * - ``lttng-iousagetop``
     - I/O usage top.
   * - ``lttng-irqfreq``
     - Interrupt handler duration frequency distribution.
   * - ``lttng-irqlog``
     - Interrupt log.
   * - ``lttng-irqstats``
     - Hardware and software interrupt statistics.
   * - ``lttng-memtop``
     - Per-TID top allocated/freed memory.
   * - ``lttng-schedfreq``
     - Scheduling latency frequency distribution.
   * - ``lttng-schedlog``
     - Scheduling top.
   * - ``lttng-schedstats``
     - Scheduling latency stats.
   * - ``lttng-schedtop``
     - Scheduling top.
   * - ``lttng-syscallstats``
     - Per-TID and global system call statistics.

Each command also has its corresponding JSON-based machine interface
version with the ``-mi`` suffix. For LTTng analyses 0.5 and after,
this machine interface is specified by the
`LTTng analyses machine interface (LAMI)
<https://github.com/lttng/lami-spec/blob/master/lami.adoc>`_ document.

Use the ``--help`` option of any command to list the descriptions
of the possible command-line options.

.. NOTE::

   You can set the ``LTTNG_ANALYSES_DEBUG`` environment variable to
   ``1`` when you launch an analysis to enable a debug output.


Examples
========

This section shows a few examples of using some LTTng analyses.

I/O
---

Partition and system call latency statistics
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   lttng-iolatencystats /path/to/trace

::

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


I/O request latency distribution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   lttng-iolatencyfreq /path/to/trace

::

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


Top system call latencies
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   lttng-iolatencytop /path/to/trace --limit=3 --minsize=2

::

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


I/O operations log
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   lttng-iolog /path/to/trace

::

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


I/O usage top
~~~~~~~~~~~~~

.. code-block:: bash

   lttng-iousagetop /path/to/trace

::

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


System calls
--------

Per-TID and global system call statistics
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   lttng-syscallstats /path/to/trace

::

    Timerange: [2015-01-15 12:18:37.216484041, 2015-01-15 12:18:53.821580313]
    Per-TID syscalls statistics (usec)
    find (22785)                          Count            Min        Average          Max      Stdev  Return values
     - getdents                           14240          0.380        364.301    43372.450   1629.390  {'success': 14240}
     - close                              14236          0.233          0.506        4.932      0.217  {'success': 14236}
     - fchdir                             14231          0.252          0.407        5.769      0.117  {'success': 14231}
     - open                                7123          0.779          2.321       12.697      0.936  {'success': 7119, 'ENOENT': 4}
     - newfstatat                          7118          1.457        143.562    28103.532   1410.281  {'success': 7118}
     - openat                              7118          1.525          2.411        9.107      0.771  {'success': 7118}
     - newfstat                            7117          0.272          0.654        8.707      0.248  {'success': 7117}
     - write                                573          0.298          0.715        8.584      0.391  {'success': 573}
     - brk                                   27          0.615          5.768       30.792      7.830  {'success': 27}
     - rt_sigaction                          22          0.227          0.283        0.589      0.098  {'success': 22}
     - mmap                                  12          1.116          2.116        3.597      0.762  {'success': 12}
     - mprotect                               6          1.185          2.235        3.923      1.148  {'success': 6}
     - read                                   5          0.925          2.101        6.300      2.351  {'success': 5}
     - ioctl                                  4          0.342          1.151        2.280      0.873  {'success': 2, 'ENOTTY': 2}
     - access                                 4          1.166          2.530        4.202      1.527  {'ENOENT': 4}
     - rt_sigprocmask                         3          0.325          0.570        0.979      0.357  {'success': 3}
     - dup2                                   2          0.250          0.562        0.874          ?  {'success': 2}
     - munmap                                 2          3.006          5.399        7.792          ?  {'success': 2}
     - execve                                 1       7277.974       7277.974     7277.974          ?  {'success': 1}
     - setpgid                                1          0.945          0.945        0.945          ?  {'success': 1}
     - fcntl                                  1              ?          0.000        0.000          ?  {}
     - newuname                               1          1.240          1.240        1.240          ?  {'success': 1}
    Total:                                71847
    -----------------------------------------------------------------------------------------------------------------
    apache2 (31517)                       Count            Min        Average          Max      Stdev  Return values
     - fcntl                                192              ?          0.000        0.000          ?  {}
     - newfstat                             156          0.237          0.484        1.102      0.222  {'success': 156}
     - read                                 144          0.307          1.602       16.307      1.698  {'success': 117, 'EAGAIN': 27}
     - access                                96          0.705          1.580        3.364      0.670  {'success': 12, 'ENOENT': 84}
     - newlstat                              84          0.459          0.738        1.456      0.186  {'success': 63, 'ENOENT': 21}
     - newstat                               74          0.735          2.266       11.212      1.772  {'success': 50, 'ENOENT': 24}
     - lseek                                 72          0.317          0.522        0.915      0.112  {'success': 72}
     - close                                 39          0.471          0.615        0.867      0.069  {'success': 39}
     - open                                  36          2.219      12162.689   437697.753  72948.868  {'success': 36}
     - getcwd                                28          0.287          0.701        1.331      0.277  {'success': 28}
     - poll                                  27          1.080       1139.669     2851.163    856.723  {'success': 27}
     - times                                 24          0.765          0.956        1.327      0.107  {'success': 24}
     - setitimer                             24          0.499          5.848       16.668      4.041  {'success': 24}
     - write                                 24          5.467          6.784       16.827      2.459  {'success': 24}
     - writev                                24         10.241         17.645       29.817      5.116  {'success': 24}
     - mmap                                  15          3.060          3.482        4.406      0.317  {'success': 15}
     - munmap                                15          2.944          3.502        4.154      0.427  {'success': 15}
     - brk                                   12          0.738          4.579       13.795      4.437  {'success': 12}
     - chdir                                 12          0.989          1.600        2.353      0.385  {'success': 12}
     - flock                                  6          0.906          1.282        2.043      0.423  {'success': 6}
     - rt_sigaction                           6          0.530          0.725        1.123      0.217  {'success': 6}
     - pwrite64                               6          1.262          1.430        1.692      0.143  {'success': 6}
     - rt_sigprocmask                         6          0.539          0.650        0.976      0.162  {'success': 6}
     - shutdown                               3          7.323          8.487       10.281      1.576  {'success': 3}
     - getsockname                            3          1.015          1.228        1.585      0.311  {'success': 3}
     - accept4                                3    5174453.611    3450157.282  5176018.235          ?  {'success': 2}
    Total:                                 1131


Interrupts
----------

Hardware and software interrupt statistics
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   lttng-irqstats /path/to/trace

::

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


Interrupt handler duration frequency distribution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   lttng-irqfreq --timerange=[16:05:42,16:05:45] --irq=44 --stats /path/to/trace

::

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


Community
=========

LTTng analyses is part of the `LTTng <http://lttng.org/>`_ project
and shares its community.

We hope you have fun trying this project and please remember it is a
work in progress; feedback, bug reports and improvement ideas are always
welcome!

.. list-table:: LTTng analyses project's communication channels
   :header-rows: 1

   * - Item
     - Location
     - Notes
   * - Mailing list
     - `lttng-dev <https://lists.lttng.org/cgi-bin/mailman/listinfo/lttng-dev>`_
       (``lttng-dev@lists.lttng.org``)
     - Preferably, use the ``[lttng-analyses]`` subject prefix
   * - IRC
     - ``#lttng`` on the OFTC network
     -
   * - Code contribution
     - Create a new GitHub
       `pull request <https://github.com/lttng/lttng-analyses/pulls>`_
     -
   * - Bug reporting
     - Create a new GitHub
       `issue <https://github.com/lttng/lttng-analyses/issues/new>`_
     -
   * - Continuous integration
     - `lttng-analyses_master_build item
       <https://ci.lttng.org/job/lttng-analyses_master_build/>`_ on
       LTTng's CI and `lttng/lttng-analyses project
       <https://travis-ci.org/lttng/lttng-analyses>`_
       on Travis CI
     -
   * - Blog
     - The `LTTng blog <http://lttng.org/blog/>`_ contains some posts
       about LTTng analyses
     -
