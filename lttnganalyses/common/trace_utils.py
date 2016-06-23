# The MIT License (MIT)
#
# Copyright (C) 2016 - Antoine Busque <abusque@efficios.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import time
import datetime
import subprocess
import sys
from .version_utils import Version
from .time_utils import NSEC_PER_SEC


BT_INTERSECT_VERSION = Version(1, 4, 0)


def is_multi_day_trace_collection_bt_1_3_2(collection, handles=None):
    """is_multi_day_trace_collection for BT < 1.3.3.

    Args:
        collection (TraceCollection): a babeltrace TraceCollection
        instance.

        handles (TraceHandle): a babeltrace TraceHandle instance.

    Returns:
        True if the trace collection spans more than one day,
        False otherwise.
    """

    time_begin = None

    for handle in handles.values():
        if time_begin is None:
            time_begin = time.localtime(handle.timestamp_begin / NSEC_PER_SEC)
            year_begin = time_begin.tm_year
            month_begin = time_begin.tm_mon
            day_begin = time_begin.tm_mday

        time_end = time.localtime(handle.timestamp_end / NSEC_PER_SEC)
        year_end = time_end.tm_year
        month_end = time_end.tm_mon
        day_end = time_end.tm_mday

        if year_begin != year_end:
            return True
        elif month_begin != month_end:
            return True
        elif day_begin != day_end:
            return True

    return False


def is_multi_day_trace_collection(collection, handles=None):
    """Check whether a trace collection spans more than one day.

    Args:
        collection (TraceCollection): a babeltrace TraceCollection
        instance.
        handles (TraceHandle): a babeltrace TraceHandle instance.

    Returns:
        True if the trace collection spans more than one day,
        False otherwise.
    """

    # Circumvent a bug in Babeltrace < 1.3.3
    if collection.timestamp_begin is None or \
            collection.timestamp_end is None:
                return is_multi_day_trace_collection_bt_1_3_2(collection,
                                                              handles)

    date_begin = datetime.date.fromtimestamp(
        collection.timestamp_begin // NSEC_PER_SEC
    )
    date_end = datetime.date.fromtimestamp(
        collection.timestamp_end // NSEC_PER_SEC
    )

    return date_begin != date_end


def get_trace_collection_date(collection, handles=None):
    """Get a trace collection's date.

    Args:
        collection (TraceCollection): a babeltrace TraceCollection
        instance.

        handles (TraceHandle): a babeltrace TraceHandle instance.

    Returns:
        A datetime.date object corresponding to the date at which the
        trace collection was recorded.

        handles (TraceHandle): a babeltrace TraceHandle instance.

    Raises:
        ValueError: if the trace collection spans more than one day.
    """
    if is_multi_day_trace_collection(collection, handles):
        raise ValueError('Trace collection spans multiple days')

    trace_date = datetime.date.fromtimestamp(
        collection.timestamp_begin // NSEC_PER_SEC
    )

    return trace_date


def get_syscall_name(event):
    """Get the name of a syscall from an event.

    Args:
        event (Event): an instance of a babeltrace Event for a syscall
        entry.

    Returns:
        The name of the syscall, stripped of any superfluous prefix.

    Raises:
        ValueError: if the event is not a syscall event.
    """
    name = event.name

    if name.startswith('sys_'):
        return name[4:]
    elif name.startswith('syscall_entry_'):
        return name[14:]
    else:
        raise ValueError('Not a syscall event')


def read_babeltrace_version():
    try:
        output = subprocess.check_output('babeltrace')
    except subprocess.CalledProcessError:
        raise ValueError('Could not run babeltrace to verify version')

    output = output.decode(sys.stdout.encoding)
    first_line = output.splitlines()[0]
    version_string = first_line.split()[-1]

    return Version.new_from_string(version_string)
