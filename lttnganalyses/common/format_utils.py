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

import math
import socket
import struct
import time
from .time_utils import NSEC_PER_SEC


def format_size(size, binary_prefix=True):
    """Convert an integral number of bytes to a human-readable string.

    Args:
        size (int): a non-negative number of bytes.

        binary_prefix (bool, optional): whether to use binary units
        prefixes, over SI prefixes (default: True).

    Returns:
        The formatted string comprised of the size and units.

    Raises:
        ValueError: if size < 0.
    """
    if size < 0:
        raise ValueError('Cannot format negative size')

    if binary_prefix:
        base = 1024
        units = ['  B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']
    else:
        base = 1000
        units = [' B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']

    if size == 0:
        exponent = 0
    else:
        exponent = int(math.log(size, base))
        if exponent >= len(units):
            # Don't try and use a unit above YiB/YB
            exponent = len(units) - 1

        size /= base ** exponent

    unit = units[exponent]

    if exponent == 0:
        # Don't display fractions of a byte
        format_str = '{:0.0f} {}'
    else:
        format_str = '{:0.2f} {}'

    return format_str.format(size, unit)


def format_prio_list(prio_list):
    """Format a list of prios into a string of unique prios with count.

    Args:
        prio_list (list): a list of PrioEvent objects.

    Returns:
        The formatted string containing the unique priorities and
        their count if they occurred more than once.
    """
    prio_count = {}
    prio_str = None

    for prio_event in prio_list:
        prio = prio_event.prio
        if prio not in prio_count:
            prio_count[prio] = 0

        prio_count[prio] += 1

    for prio in sorted(prio_count.keys()):
        count = prio_count[prio]
        if count > 1:
            count_str = ' ({} times)'.format(count)
        else:
            count_str = ''

        if prio_str is None:
            prio_str = '[{}{}'.format(prio, count_str)
        else:
            prio_str += ', {}{}'.format(prio, count_str)

    if prio_str is None:
        prio_str = '[]'
    else:
        prio_str += ']'

    return prio_str


def format_timestamp(timestamp, print_date=False, gmt=False):
    """Format a timestamp into a human-readable date string

    Args:
        timestamp (int): nanoseconds since epoch.

        print_date (bool, optional): flag indicating whether to print
        the full date or just the time of day (default: False).

        gmt (bool, optional): flag indicating whether the timestamp is
        in the local timezone or gmt (default: False).

    Returns:
        The formatted date string, containing either the full date or
        just the time of day.
    """
    date_fmt = '{:04}-{:02}-{:02} '
    time_fmt = '{:02}:{:02}:{:02}.{:09}'

    if gmt:
        date = time.gmtime(timestamp // NSEC_PER_SEC)
    else:
        date = time.localtime(timestamp // NSEC_PER_SEC)

    formatted_ts = time_fmt.format(
        date.tm_hour, date.tm_min, date.tm_sec,
        timestamp % NSEC_PER_SEC
    )

    if print_date:
        date_str = date_fmt.format(date.tm_year, date.tm_mon, date.tm_mday)
        formatted_ts = date_str + formatted_ts

    return formatted_ts


def format_time_range(begin_ts, end_ts, print_date=False, gmt=False):
    """Format a pair of timestamps into a human-readable date string.

    Args:
        begin_ts (int): nanoseconds since epoch to beginning of
        time range.

        end_ts (int): nanoseconds since epoch to end of time range.

        print_date (bool, optional): flag indicating whether to print
        the full date or just the time of day (default: False).

        gmt (bool, optional): flag indicating whether the timestamp is
        in the local timezone or gmt (default: False).

    Returns:
        The formatted dates string, containing either the full date or
        just the time of day, enclosed within square brackets and
        delimited by a comma.
    """
    time_range_fmt = '[{}, {}]'

    begin_str = format_timestamp(begin_ts, print_date, gmt)
    end_str = format_timestamp(end_ts, print_date, gmt)

    return time_range_fmt.format(begin_str, end_str)


def format_ipv4(ip, port=None):
    """Format an ipv4 address into a human-readable string.

    Args:
        ip (varies): the ip address as extracted in an LTTng event.
        Either an integer or a list of integers, depending on the
        tracer version.

        port (int, optional): the port number associated with the
        address.

    Returns:
        The formatted string containing the ipv4 address and, optionally,
        the port number.

    """
    # depending on the version of lttng-modules, the v4addr is an
    # integer (< 2.6) or sequence (>= 2.6)
    try:
        ip_str = '{}.{}.{}.{}'.format(ip[0], ip[1], ip[2], ip[3])
    except TypeError:
        # The format string '!I' tells pack to interpret ip as a
        # packed structure of network-endian 32-bit unsigned integers,
        # which inet_ntoa can then convert into the formatted string
        ip_str = socket.inet_ntoa(struct.pack('!I', ip))

    if port is not None:
        ip_str += ':{}'.format(port)

    return ip_str
