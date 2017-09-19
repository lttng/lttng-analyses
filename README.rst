LTTng analyses
**************

.. image:: https://img.shields.io/pypi/v/lttnganalyses.svg?label=Latest%20version
   :target: https://pypi.python.org/pypi/lttnganalyses
   :alt: Latest version released on PyPi

.. image:: https://travis-ci.org/lttng/lttng-analyses.svg?branch=master&label=Travis%20CI%20build
   :target: https://travis-ci.org/lttng/lttng-analyses
   :alt: Status of Travis CI

.. image:: https://img.shields.io/jenkins/s/https/ci.lttng.org/lttng-analyses_master_build.svg?label=LTTng%20CI%20build
   :target: https://ci.lttng.org/job/lttng-analyses_master_build
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

**Current limitations**:

- The LTTng analyses can be quite slow to execute. There are a number of
  places where they could be optimized, but using the Python interpreter
  seems to be an important impediment.

  This project is regarded by its authors as a testing ground to
  experiment analysis features, user interfaces, and usability in
  general. It is not considered ready to analyze long traces.

**Contents**:

.. contents::
   :local:
   :depth: 3
   :backlinks: none


Install LTTng analyses
======================

Required dependencies
---------------------

- `Python <https://www.python.org/>`_ ≥ 3.4
- `setuptools <https://pypi.python.org/pypi/setuptools>`_
- `pyparsing <http://pyparsing.wikispaces.com/>`_ ≥ 2.0.0
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

   Note that you can also install LTTng analyses locally, only for
   your user:

   .. code-block:: bash

      pip3 install --user --upgrade lttnganalyses

   Files are installed in ``~/.local``, therefore ``~/.local/bin`` must
   be part of your ``PATH`` environment variable for the LTTng analyses
   to be launchable.


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

      sudo pip3 install --upgrade git+git://github.com/lttng/lttng-analyses.git@master

   Replace ``master`` with the desired branch or tag name to install
   in the previous URL.

   Note that you can also install LTTng analyses locally, only for
   your user:

   .. code-block:: bash

      sudo pip3 install --user --upgrade git+git://github.com/lttng/lttng-analyses.git@master

   Files are installed in ``~/.local``, therefore ``~/.local/bin`` must
   be part of your ``PATH`` environment variable for the LTTng analyses
   to be launchable.


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

   On Ubuntu > 12.04:

   .. code-block:: bash

      sudo apt-get install -y python3-pyparsing

   On Ubuntu 12.04:

   .. code-block:: bash

      sudo pip3 install --upgrade pyparsing
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
      sudo apt-get install -y python3-pyparsing
#. **Optional**: Install the optional dependencies:

   .. code-block:: bash

      sudo apt-get install -y lttng-tools
      sudo apt-get install -y lttng-modules-dkms
      sudo apt-get install -y python3-progressbar
      sudo apt-get install -y python3-termcolor
#. Install LTTng analyses:

   .. code-block:: bash

      sudo apt-get install -y python3-lttnganalyses


Sample traces
=============

If you just want to try the tools, a sample trace is available
`here <http://www.lttng.org/files/analysis-20150115-120942.tar.gz>`_.

If you want to see a step-by-step usage of these tools to identify a single
unusual request latency, you can check this
`blog post <https://lttng.org/blog/2015/02/04/web-request-latency-root-cause/>`_,
it shows how to navigate in the sample trace and accurately find the culprit.


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

#. Launch the installed script:

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
      sudo lttng enable-event --kernel --channel=chan block_rq_complete
      sudo lttng enable-event --kernel --channel=chan block_rq_issue
      sudo lttng enable-event --kernel --channel=chan irq_handler_entry
      sudo lttng enable-event --kernel --channel=chan irq_handler_exit
      sudo lttng enable-event --kernel --channel=chan irq_softirq_entry
      sudo lttng enable-event --kernel --channel=chan irq_softirq_exit
      sudo lttng enable-event --kernel --channel=chan irq_softirq_raise
      sudo lttng enable-event --kernel --channel=chan kmem_mm_page_alloc
      sudo lttng enable-event --kernel --channel=chan kmem_mm_page_free
      sudo lttng enable-event --kernel --channel=chan lttng_statedump_block_device
      sudo lttng enable-event --kernel --channel=chan lttng_statedump_file_descriptor
      sudo lttng enable-event --kernel --channel=chan lttng_statedump_process_state
      sudo lttng enable-event --kernel --channel=chan mm_page_alloc
      sudo lttng enable-event --kernel --channel=chan mm_page_free
      sudo lttng enable-event --kernel --channel=chan net_dev_xmit
      sudo lttng enable-event --kernel --channel=chan netif_receive_skb
      sudo lttng enable-event --kernel --channel=chan sched_pi_setprio
      sudo lttng enable-event --kernel --channel=chan sched_process_exec
      sudo lttng enable-event --kernel --channel=chan sched_process_fork
      sudo lttng enable-event --kernel --channel=chan sched_switch
      sudo lttng enable-event --kernel --channel=chan sched_wakeup
      sudo lttng enable-event --kernel --channel=chan sched_waking
      sudo lttng enable-event --kernel --channel=chan softirq_entry
      sudo lttng enable-event --kernel --channel=chan softirq_exit
      sudo lttng enable-event --kernel --channel=chan softirq_raise
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


Run an LTTng analysis
=====================

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
   * - ``lttng-periodlog``
     - Period log.
   * - ``lttng-periodstats``
     - Period duration stats.
   * - ``lttng-periodtop``
     - Period duration top.
   * - ``lttng-periodfreq``
     - Period duration frequency distribution.
   * - ``lttng-syscallstats``
     - Per-TID and global system call statistics.

Use the ``--help`` option of any command to list the descriptions
of the possible command-line options.

.. NOTE::

   You can set the ``LTTNG_ANALYSES_DEBUG`` environment variable to
   ``1`` when you launch an analysis to enable a debug output. You can
   also use the general ``--debug`` option.


Filtering options
-----------------

Depending on the analysis, filter options are available. The complete
list of filter options is:

.. list-table:: Available filtering command-line options
   :header-rows: 1

   * - Command-line option
     - Description
   * - ``--begin``
     - Trace time at which to begin the analysis.

       Format: ``HH:MM:SS[.NNNNNNNNN]``.
   * - ``--cpu``
     - Comma-delimited list of CPU IDs for which to display the
       results.
   * - ``--end``
     - Trace time at which to end the analysis.

       Format: ``HH:MM:SS[.NNNNNNNNN]``.
   * - ``--irq``
     - List of hardware IRQ numbers for which to display the results.
   * - ``--limit``
     - Maximum number of output rows per table. This option is useful
       for "top" analyses, like ``lttng-cputop``.
   * - ``--min``
     - Minimum duration (µs) to keep in results.
   * - ``--minsize``
     - Minimum I/O operation size (B) to keep in results.
   * - ``--max``
     - Maximum duration (µs) to keep in results.
   * - ``--maxsize``
     - Maximum I/O operation size (B) to keep in results.
   * - ``--procname``
     - Comma-delimited list of process names for which to display
       the results.
   * - ``--softirq``
     - List of software IRQ numbers for which to display the results.
   * - ``--tid``
     - Comma-delimited list of thread IDs for which to display the
       results.


Period options
--------------

LTTng analyses feature a powerful "period engine". A *period* is an
interval which begins and ends under specific conditions. When the
analysis results are displayed, they are isolated for the periods
that were opened and closed during the process.

A period can have a parent. If it's the case, then its parent needs
to exist for the period to begin at all. This tree structure of
periods is useful to keep a form of custom user state during the
generic kernel analysis.

.. ATTENTION::

   The ``--period`` and ``--period-captures`` options's arguments
   include characters that are considered special by most shells,
   like ``$``, ``*``, and ``&``.

   Make sure to always **single-quote** those arguments when running
   the LTTng analyses on the command line.


Period definition
~~~~~~~~~~~~~~~~~

You can define one or more periods on the command line, when launching
an analysis, with the ``--period`` option. This option's argument
accepts the following form (content within square brackets is optional)::

    [ NAME [ (PARENT) ] ] : BEGINEXPR [ : ENDEXPR ]

``NAME``
  Optional name of the period definition. All periods opened from this
  definition have this name.

  The syntax of this name is the same as a C identifier.

``PARENT``
  Optional name of a *previously defined* period which acts as the
  parent period definition of this definition.

  ``NAME`` must be set for ``PARENT`` to be set.

``BEGINEXPR``
  Matching expression which a given event must match in order for an
  actual period to be instantiated by this definition.

``ENDEXPR``
  Matching expression which a given event must match in order for an
  instance of this definition to be closed.

  If this part is omitted, ``BEGINEXPR`` is used for the ending
  expression too.


Matching expression
...................

A matching expression is a C-like logical expression. It supports
nesting expressions with ``(`` and ``)``, as well as the ``&&`` (logical
*AND*), ``||`` (logical *OR*), and ``!`` (logical *NOT*) operators. The
precedence of those operators is the same as in the C language.

The atomic operands in those logical expressions are comparisons. For
the following comparison syntaxes, consider that:

- ``EVT`` indicates an event source. The available event sources are:

  ``$evt``
    Current event.

  ``$begin.$evt``
    In ``BEGINEXPR``: current event (same as ``$evt``).

    In ``ENDEXPR``: event which, for this period instance, was matched
    when ``BEGINEXPR`` was evaluated.

  ``$parent.$begin.$evt``
    Event which, for the parent period instance of this period instance,
    was matched when ``BEGINEXPR`` of the parent was evaluated.
- ``FIELD`` indicates an event field source. The available event field
  sources are:

  ``NAME`` (direct field name)
    Automatic scope: try to find the field named ``NAME`` in the dynamic
    scopes in this order:

    #. Event payload
    #. Event context
    #. Event header
    #. Stream event context
    #. Packet context
    #. Packet header

  ``$payload.NAME``
    Event payload field named ``NAME``.

  ``$ctx.NAME``
    Event context field named ``NAME``.

  ``$header.NAME``
    Event header field named ``NAME``.

  ``$stream_ctx.NAME``
    Stream event context field named ``NAME``.

  ``$pkt_ctx.NAME``
    Packet context field named ``NAME``.

  ``$pkt_header.NAME``
    Packet header field named ``NAME``.
- ``VALUE`` indicates one of:

  - A constant, decimal number. This can be an integer or a real
    number, positive or negative, and supports the ``e`` scientific
    notation.

    Examples: ``23``, ``-18.28``, ``7.2e9``.
  - A double-quoted literal string. ``"`` and ``\`` can be escaped
    with ``\``.

    Examples: ``"hello, world!"``, ``"here's another \"quoted\" string"``.
  - An event field, that is, ``EVT.FIELD``, considering the replacements
    described above.

- ``NUMVALUE`` indicates one of:

  - A constant, decimal number. This can be an integer or a real
    number, positive or negative, and supports the ``e`` scientific
    notation.

    Examples: ``23``, ``-18.28``, ``7.2e9``.
  - An event field, that is, ``EVT.FIELD``, considering the replacements
    described above.

.. list-table:: Available comparison syntaxes for matching expressions
   :header-rows: 1

   * - Comparison syntax
     - Description
   * - #. ``EVT.$name == "NAME"``
       #. ``EVT.$name != "NAME"``
       #. ``EVT.$name =* "PATTERN"``
     - Name matching:

       #. Name of event source ``EVT`` is equal to ``NAME``.
       #. Name of event source ``EVT`` is not equal to ``NAME``.
       #. Name of event source ``EVT`` satisfies the globbing pattern
          ``PATTERN``
          (see `fnmatch <https://docs.python.org/3/library/fnmatch.html>`_).
   * - #. ``EVT.FIELD == VALUE``
       #. ``EVT.FIELD != VALUE``
       #. ``EVT.FIELD < NUMVALUE``
       #. ``EVT.FIELD <= NUMVALUE``
       #. ``EVT.FIELD > NUMVALUE``
       #. ``EVT.FIELD >= NUMVALUE``
       #. ``EVT.FIELD =* "PATTERN"``
     - Value matching:

       #. The value of the field ``EVT.FIELD`` is equal
          to the value ``VALUE``.
       #. The value of the field ``EVT.FIELD`` is not
          equal to the value ``VALUE``.
       #. The value of the field ``EVT.FIELD`` is lesser
          than the value ``NUMVALUE``.
       #. The value of the field ``EVT.FIELD`` is lesser
          than or equal to the value ``NUMVALUE``.
       #. The value of the field ``EVT.FIELD`` is greater
          than the value ``NUMVALUE``.
       #. The value of the field ``EVT.FIELD`` is greater
          than or equal to the value ``NUMVALUE``.
       #. The value of the field ``EVT.FIELD`` satisfies
          the globbing pattern ``PATTERN``
          (see `fnmatch <https://docs.python.org/3/library/fnmatch.html>`_).

In any case, if ``EVT.FIELD`` does not target an existing field, the
comparison including it fails. Also, string fields cannot be compared to
number values (constant or fields).


Examples
........

- Create a period instance named ``switch`` when:

  - The current event name is ``sched_switch``.

  End this period instance when:

  - The current event name is ``sched_switch``.

  Period definition::

      switch : $evt.$name == "sched_switch"

- Create a period instance named ``switch`` when:

  - The current event name is ``sched_switch`` *AND*
  - The current event's ``next_tid`` field is *NOT* equal to 0.

  End this period instance when:

  - The current event name is ``sched_switch`` *AND*
  - The current event's ``prev_tid`` field is equal to
    the ``next_tid`` field of the matched event in the begin expression *AND*
  - The current event's ``cpu_id`` field is equal to
    the ``cpu_id`` field of the matched event in the begin expression.

  Period definition::

      switch
      : $evt.$name == "sched_switch" &&
        $evt.next_tid != 0
      : $evt.$name == "sched_switch" &&
        $evt.prev_tid == $begin.$evt.next_tid &&
        $evt.cpu_id == $begin.$evt.cpu_id

- Create a period instance named ``irq`` when:

  - A parent period instance named ``switch`` is currently opened.
  - The current event name satisfies the ``irq_*_entry`` globbing
    pattern *AND*
  - The current event's ``cpu_id`` field is equal to the ``cpu_id``
    field of the matched event in the begin expression of the parent
    period instance.

  End this period instance when:

  - The current event name is ``irq_handler_exit`` *AND*
  - The current event's ``cpu_id`` field is equal to
    the ``cpu_id`` field of the matched event in the begin expression.

  Period definition::

      irq(switch)
      : $evt.$name =* "irq_*_entry" &&
        $evt.cpu_id == $parent.$begin.$evt.cpu_id
      : $evt.$name == "irq_handler_exit" &&
        $evt.cpu_id == $begin.$evt.cpu_id

- Create a period instance named ``hello`` when:

  - The current event name satisfies the ``hello*`` globbing pattern,
    but excludes ``hello world``.

  End this period instance when:

  - The current event name is the same as the name of the matched event
    in the begin expression *AND*
  - The current event's ``theid`` header field is lesser than or equal
    to 231.

  Period definition::

      hello
      : $evt.$name =* "hello*" &&
        $evt.$name != "hello world"
      : $evt.$name == $begin.$evt.$name &&
        $evt.$header.theid <= 231


Period captures
~~~~~~~~~~~~~~~

When a period instance begins or ends, the analysis can capture the
current values of specific event fields and display them in its
results.

You can set period captures with the ``--period-captures`` command-line
option. This option's argument accepts the following form
(content within square brackets is optional)::

    NAME : BEGINCAPTURES [ : ENDCAPTURES ]

``NAME``
  Name of period instances on which to apply those captures.

  A ``--period`` option in the same command line must define this name.

``BEGINCAPTURES``
  Comma-delimited list of event fields to capture when the beginning
  expression of the period definition named ``NAME`` is matched.

``ENDCAPTURES``
  Comma-delimited list of event fields to capture when the ending
  expression of the period definition named ``NAME`` is matched.

  If this part is omitted, there are no end captures.

The format of ``BEGINCAPTURES`` and ``ENDCAPTURES`` is a comma-delimited
list of tokens having this format::

    [ CAPTURENAME = ] EVT.FIELD

or::

    [ CAPTURENAME = ] EVT.$name

``CAPTURENAME``
  Custom name for this capture. The syntax of this name is the same as
  a C identifier.

  If this part is omitted, the literal expression used for ``EVT.FIELD``
  is used.

``EVT`` and ``FIELD``
  See `Matching expression`_.


Period select and aggregate parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

With ``lttng-periodlog``, it is possible to see the list of periods in the
context of their parent. By specifying the ``--aggregate-by``, the lines in
the log present on the same line the timerange of the period specified by
the ``--select`` argument at the timerange of the parent period that contains
it. In ``lttng-periodstats`` and ``lttng-periodfreq``, these two flags are
used as filter to limit the output to only the relevant periods. If omitted,
all existing combinations of parent/child statistics and frequency
distributions are output.


Grouping
~~~~~~~~

When fields are captured during the period analyses, it is possible to compute
the statistics and frequency distribution grouped by values of the these
fields, instead of globally for the trace. The format is::

    --group-by "PERIODNAME.CAPTURENAME[, PERIODNAME.CAPTURENAME]"

If multiple values are passed, the analysis outputs one list of tables
(statistics and/or frequency distribution) for each unique combination of the
field's values.

For example, if we track the ``open`` system call and we are interested in the
average duration of this call by filename, we only have to capture the filename
field and group the results by ``open.filename``.


Examples
........

Begin captures only::

    switch
    : $evt.next_tid,
      name = $evt.$name,
      msg_id = $parent.$begin.$evt.id

Begin and end captures::

    hello
    : beginning = $evt.$ctx.begin_ts,
      $evt.received_bytes
    : $evt.send_bytes,
      $evt.$name,
      begin = $begin.$evt.$ctx.begin_ts
      end = $evt.$ctx.end_ts

Top scheduling latency (delay between ``sched_waking(tid=$TID)`` and ``sched_switch(next_tid=$TID)``)
with recording of the procname of the waker (dependant of the ``procname`` context in the trace),
priority and target CPU:

.. code-block:: bash

   lttng-periodtop /path/to/trace \
       --period 'wake : $evt.$name == "sched_waking" : $evt.$name == "sched_switch" && $evt.next_tid == $begin.$evt.$payload.tid' \
       --period-capture 'wake : waker = $evt.procname, prio = $evt.prio : wakee = $evt.next_comm, cpu = $evt.cpu_id'

::

    Timerange: [2016-07-21 17:07:47.832234248, 2016-07-21 17:07:48.948152659]
    Period top
    Begin                End                   Duration (us) Name            Begin capture                       End capture
    [17:07:47.835338581, 17:07:47.946834976]      111496.395 wake            waker = lttng-consumerd             wakee = kworker/0:2
                                                                             prio = 20                           cpu = 0
    [17:07:47.850409057, 17:07:47.946829256]       96420.199 wake            waker = swapper/2                   wakee = migration/0
                                                                             prio = -100                         cpu = 0
    [17:07:48.300313282, 17:07:48.300993892]         680.610 wake            waker = Xorg                        wakee = ibus-ui-gtk3
                                                                             prio = 20                           cpu = 3
    [17:07:48.300330060, 17:07:48.300920648]         590.588 wake            waker = Xorg                        wakee = ibus-x11
                                                                             prio = 20                           cpu = 3


Log of all the IRQ handled while a user-space process was running, capture the procname of the process interrupted, the name and number of the IRQ:

.. code-block:: bash

    lttng-periodlog /path/to/trace \
        --period 'switch : $evt.$name == "sched_switch" && $evt.next_tid != 0 : $evt.$name == "sched_switch" && $evt.prev_tid == $begin.$evt.next_tid && $evt.cpu_id == $begin.$evt.cpu_id' \
        --period 'irq(switch) : $evt.$name == "irq_handler_entry" && $evt.cpu_id == $parent.$begin.$evt.cpu_id : $evt.$name == "irq_handler_exit" && $evt.cpu_id == $begin.$evt.cpu_id' \
        --period-capture 'irq : name = $evt.name, irq = $evt.irq, current = $parent.$begin.$evt.next_comm'

::

    Period log
    Begin                End                   Duration (us) Name            Begin capture                       End capture
    [10:58:26.169238875, 10:58:26.169244920]           6.045 switch
    [10:58:26.169598385, 10:58:26.169602967]           4.582 irq             name = ahci
                                                                             irq = 41
                                                                             current = lttng-consumerd
    [10:58:26.169811553, 10:58:26.169816218]           4.665 irq             name = ahci
                                                                             irq = 41
                                                                             current = lttng-consumerd
    [10:58:26.170025600, 10:58:26.170030197]           4.597 irq             name = ahci
                                                                             irq = 41
                                                                             current = lttng-consumerd
    [10:58:26.169236842, 10:58:26.170105711]         868.869 switch


Log of all the ``open`` system call periods aggregated by the ``sched_switch`` in which they occurred:

.. code-block:: bash

    lttng-periodlog /path/to/trace \
        --period 'switch : $evt.$name == "sched_switch" : $evt.$name == "sched_switch" && $begin.$evt.next_tid == $evt.prev_tid && $begin.$evt.cpu_id == $evt.cpu_id' \
        --period 'open(switch) : $evt.$name == "syscall_entry_open" && $parent.$begin.$evt.cpu_id == $evt.cpu_id : $evt.$name == "syscall_exit_open" && $begin.$evt.cpu_id == $evt.cpu_id' \
        --period-captures 'switch : comm = $evt.next_comm, cpu = $evt.cpu_id, tid = $evt.next_tid' \
        --period-captures 'open : filename = $evt.filename : fd = $evt.ret' \
        --select open
        --aggregate-by switch

::

    Aggregated log
    Aggregation of (open) by switch
                                        Parent                                  |                                     |                           Durations (us)                        |
    Begin                End                      Duration (us) Name            | Child name                    Count |        Min          Avg          Max         Stdev      Runtime | Parent captures
    [10:58:26.222823677, 10:58:26.224039381]           1215.704 switch          | switch/open                       3 |      7.517        9.548       11.248        1.887        28.644 | switch.comm = bash, switch.cpu = 3, switch.tid = 12420
    [10:58:26.856224058, 10:58:26.856589867]            365.809 switch          | switch/open                       1 |     77.620       77.620       77.620            ?        77.620 | switch.comm = ntpd, switch.cpu = 0, switch.tid = 11132
    [10:58:27.000068031, 10:58:27.000954859]            886.828 switch          | switch/open                      15 |      9.224       16.126       37.190        6.681       241.894 | switch.comm = irqbalance, switch.cpu = 0, switch.tid = 1656
    [10:58:27.225474282, 10:58:27.229160014]           3685.732 switch          | switch/open                      22 |      5.797        6.767        9.308        0.972       148.881 | switch.comm = bash, switch.cpu = 1, switch.tid = 12421


Statistics about the memory allocation performed within an ``open`` system call
within a single ``sched_switch`` (no blocking or preemption):

.. code-block:: bash

    lttng-periodstats /path/to/trace \
        --period 'switch : $evt.$name == "sched_switch" : $evt.$name == "sched_switch" && $begin.$evt.next_tid == $evt.prev_tid && $begin.$evt.cpu_id == $evt.cpu_id' \
        --period 'open(switch) : $evt.$name == "syscall_entry_open" && $parent.$begin.$evt.cpu_id == $evt.cpu_id : $evt.$name == "syscall_exit_open" && $begin.$evt.cpu_id == $evt.cpu_id' \
        --period 'alloc(open) : $evt.$name == "kmem_cache_alloc" && $parent.$begin.$evt.cpu_id == $evt.cpu_id : $evt.$name == "kmem_cache_free" && $evt.ptr == $begin.$evt.ptr' \
        --period-captures 'switch : comm = $evt.next_comm, cpu = $evt.cpu_id, tid = $evt.next_tid' \
        --period-captures 'open : filename = $evt.filename : fd = $evt.ret' \
        --period-captures 'alloc : ptr = $evt.ptr'

::

   Timerange: [2015-01-06 10:58:26.140545481, 2015-01-06 10:58:27.229358936]
   Period tree:
   switch
   |-- open
       |-- alloc

   Period statistics (us)
   Period                       Count           Min           Avg           Max         Stdev      Runtime
   switch                         831         2.824      5233.363    172056.802     16197.531  4348924.614
   switch/open                     41         5.797        12.123        77.620        12.076      497.039
   switch/open/alloc               44         1.152        10.277        74.476        11.582      452.175

   Per-parent period duration statistics (us)
   With active children
   Period                    Parent                              Min           Avg           Max         Stdev
   switch/open               switch                           28.644       124.260       241.894        92.667
   switch/open/alloc         switch                           24.036       113.044       229.713        87.827
   switch/open/alloc         switch/open                       4.550        11.029        74.476        11.768

   Per-parent duration ratio (%)
   With active children
   Period                    Parent                              Min           Avg           Max         Stdev
   switch/open               switch                                2        13.723            27        12.421
   switch/open/alloc         switch                                1        12.901            25        12.041
   switch/open/alloc         switch/open                          76        88.146           115         7.529

   Per-parent period count statistics
   With active children
   Period                    Parent                              Min           Avg           Max         Stdev
   switch/open               switch                                1        10.250            22         9.979
   switch/open/alloc         switch                                1        11.000            22        10.551
   switch/open/alloc         switch/open                           1         1.073             2         0.264

   Per-parent period duration statistics (us)
   Globally
   Period                    Parent                              Min           Avg           Max         Stdev
   switch/open               switch                            0.000         0.598       241.894        10.251
   switch/open/alloc         switch                            0.000         0.544       229.713         9.443
   switch/open/alloc         switch/open                       4.550        11.029        74.476        11.768

   Per-parent duration ratio (%)
   Globally
   Period                    Parent                              Min           Avg           Max         Stdev
   switch/open               switch                                0         0.066            27         1.209
   switch/open/alloc         switch                                0         0.062            25         1.150
   switch/open/alloc         switch/open                          76        88.146           115         7.529

   Per-parent period count statistics
   Globally
   Period                    Parent                              Min           Avg           Max         Stdev
   switch/open               switch                                0         0.049            22         0.929
   switch/open/alloc         switch                                0         0.053            22         0.991
   switch/open/alloc         switch/open                           1         1.073             2         0.264


These statistics can also be scoped by value of the FD returned by the ``open``
system, by appending ``--group-by "open.fd"`` to the previous command line.
That way previous tables will be output for each value of FD returned, so it
is possible to observe the behaviour based on the parameters of a system call.

Using the ``lttng-periodfreq`` or the ``--freq`` parameter, these tables can
also be presented as frequency distributions.


Progress options
----------------

If the `progressbar <https://pypi.python.org/pypi/progressbar/>`_
optional dependency is installed, a progress bar is available to
indicate the progress of the analysis.

By default, the progress bar is based on the current event's timestamp.

Progress options are:

.. list-table:: Available progress command-line options
   :header-rows: 1

   * - Command-line option
     - Description
   * - ``--no-progress``
     - Disable the progress bar.
   * - ``--progress-use-size``
     - Use the approximate event size instead of the current event's
       timestamp to estimate the progress value.


Machine interface
-----------------

If you want to display LTTng analyses results in a custom viewer,
you can use the JSON-based LTTng analyses machine interface (LAMI).
Each command in the previous table has its corresponding LAMI version
with the ``-mi`` suffix. For example, the LAMI version of
``lttng-cputop`` is ``lttng-cputop-mi``.

This version of LTTng analyses conforms to
`LAMI 1.0 <http://lttng.org/files/lami/lami-1.0.1.html>`_.

The LAMI output can be used in TraceCompass (>=2.1) to create graphs based
on the output of the scripts.



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
