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

import datetime
from .time_utils import NSEC_PER_SEC


def is_multi_day_trace_collection(collection):
    """Check whether a trace collection spans more than one day.

    Args:
        collection (TraceCollection): a babeltrace TraceCollection
        instance.

    Returns:
        True if the trace collection spans more than one day,
        False otherwise.
    """
    date_begin = datetime.date.fromtimestamp(
        collection.timestamp_begin / NSEC_PER_SEC
    )
    date_end = datetime.date.fromtimestamp(
        collection.timestamp_end / NSEC_PER_SEC
    )

    return date_begin != date_end


def get_trace_collection_date(collection):
    """Get a trace collection's date.

    Args:
        collection (TraceCollection): a babeltrace TraceCollection
        instance.

    Returns:
        A datetime.date object corresponding to the date at which the
        trace collection was recorded.

    Raises:
        ValueError: if the trace collection spans more than one day.
    """
    if is_multi_day_trace_collection(collection):
        raise ValueError('Trace collection spans multiple days')

    trace_date = datetime.date.fromtimestamp(
        collection.timestamp_begin / NSEC_PER_SEC
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
