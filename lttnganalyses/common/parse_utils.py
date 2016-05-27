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
import re
from time import timezone
from . import trace_utils
from .time_utils import NSEC_PER_SEC


def _split_value_units(raw_str):
    """Take a string with a numerical value and units, and separate the
    two.

    Args:
        raw_str (str): the string to parse, with numerical value and
        (optionally) units.

    Returns:
        A tuple (value, units), where value is a string and units is
        either a string or `None` if no units were found.
    """
    try:
        units_index = next(i for i, c in enumerate(raw_str) if c.isalpha())
    except StopIteration:
        # no units found
        return (raw_str, None)

    return (raw_str[:units_index], raw_str[units_index:])


def parse_size(size_str):
    """Convert a human-readable size string to an integral number of
    bytes.

    Args:
        size_str (str): the formatted string comprised of the size and
        units.

    Returns:
        A number of bytes.

    Raises:
        ValueError: if units are unrecognised or the size is not a
        real number.
    """
    binary_units = ['B', 'KiB', 'MiB', 'GiB', 'TiB',
                    'PiB', 'EiB', 'ZiB', 'YiB']
    # units as printed by GNU coreutils (e.g. ls or du), using base
    # 1024 as well
    coreutils_units = ['B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']
    si_units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']

    size, units = _split_value_units(size_str)

    try:
        size = float(size)
    except ValueError:
        raise ValueError('invalid size: {}'.format(size))

    # If no units have been found, assume bytes
    if units is not None:
        if units in binary_units:
            base = 1024
            exponent = binary_units.index(units)
        elif units in coreutils_units:
            base = 1024
            exponent = coreutils_units.index(units)
        elif units in si_units:
            base = 1000
            exponent = si_units.index(units)
        else:
            raise ValueError('unrecognised units: {}'.format(units))

        size *= base ** exponent

    return int(size)


def parse_duration(duration_str):
    """Convert a human-readable duration string to an integral number of
    nanoseconds.

    Args:
        duration_str (str): the formatted string comprised of the
        duration and units.

    Returns:
        A number of nanoseconds.

    Raises:
        ValueError: if units are unrecognised or the size is not a
        real number.
    """
    base = 1000
    duration, units = _split_value_units(duration_str)

    try:
        duration = float(duration)
    except ValueError:
        raise ValueError('invalid duration: {}'.format(duration))

    if units is not None:
        if units == 's':
            exponent = 3
        elif units == 'ms':
            exponent = 2
        elif units in ['us', 'µs']:
            exponent = 1
        elif units == 'ns':
            exponent = 0
        else:
            raise ValueError('unrecognised units: {}'.format(units))
    else:
        # no units defaults to seconds
        exponent = 3

    duration *= base ** exponent

    return int(duration)


def _parse_date_full_with_nsec(date):
    """Parse full date string with nanosecond resolution.

    This matches either 2014-12-12 17:29:43.802588035 or
    2014-12-12T17:29:43.802588035.

    Args:
        date (str): the date string to be parsed.

    Returns:
        A tuple of the format (date_time, nsec), where date_time is a
        datetime.datetime object and nsec is an int of the remaining
        nanoseconds.

    Raises:
        ValueError: if the date format does not match.
    """
    pattern = re.compile(
        r'^(?P<year>\d{4})-(?P<mon>[01]\d)-(?P<day>[0-3]\d)[\sTt]'
        r'(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\.(?P<nsec>\d{9})$'
    )

    if not pattern.match(date):
        raise ValueError('Wrong date format: {}'.format(date))

    year = pattern.search(date).group('year')
    month = pattern.search(date).group('mon')
    day = pattern.search(date).group('day')
    hour = pattern.search(date).group('hour')
    minute = pattern.search(date).group('min')
    sec = pattern.search(date).group('sec')
    nsec = pattern.search(date).group('nsec')

    date_time = datetime.datetime(
        int(year), int(month), int(day),
        int(hour), int(minute), int(sec)
    )

    return date_time, int(nsec)


def _parse_date_full(date):
    """Parse full date string.

    This matches either 2014-12-12 17:29:43 or 2014-12-12T17:29:43.

    Args:
        date (str): the date string to be parsed.

    Returns:
        A tuple of the format (date_time, nsec), where date_time is a
        datetime.datetime object and nsec is 0.

    Raises:
        ValueError: if the date format does not match.
    """
    pattern = re.compile(
        r'^(?P<year>\d{4})-(?P<mon>[01]\d)-(?P<day>[0-3]\d)[\sTt]'
        r'(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})$'
    )

    if not pattern.match(date):
        raise ValueError('Wrong date format: {}'.format(date))

    year = pattern.search(date).group('year')
    month = pattern.search(date).group('mon')
    day = pattern.search(date).group('day')
    hour = pattern.search(date).group('hour')
    minute = pattern.search(date).group('min')
    sec = pattern.search(date).group('sec')
    nsec = 0

    date_time = datetime.datetime(
        int(year), int(month), int(day),
        int(hour), int(minute), int(sec)
    )

    return date_time, nsec


def _parse_date_time_with_nsec(date):
    """Parse time string with nanosecond resolution.

    This matches 17:29:43.802588035.

    Args:
        date (str): the date string to be parsed.

    Returns:
        A tuple of the format (date_time, nsec), where date_time is a
        datetime.time object and nsec is an int of the remaining
        nanoseconds.

    Raises:
        ValueError: if the date format does not match.
    """
    pattern = re.compile(
        r'^(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\.(?P<nsec>\d{9})$'
    )

    if not pattern.match(date):
        raise ValueError('Wrong date format: {}'.format(date))

    hour = pattern.search(date).group('hour')
    minute = pattern.search(date).group('min')
    sec = pattern.search(date).group('sec')
    nsec = pattern.search(date).group('nsec')

    time = datetime.time(int(hour), int(minute), int(sec))

    return time, int(nsec)


def _parse_date_time(date):
    """Parse time string.

    This matches 17:29:43.

    Args:
        date (str): the date string to be parsed.

    Returns:
        A tuple of the format (date_time, nsec), where date_time is a
        datetime.time object and nsec is 0.

    Raises:
        ValueError: if the date format does not match.
    """
    pattern = re.compile(
        r'^(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})$'
    )

    if not pattern.match(date):
        raise ValueError('Wrong date format: {}'.format(date))

    hour = pattern.search(date).group('hour')
    minute = pattern.search(date).group('min')
    sec = pattern.search(date).group('sec')
    nsec = 0

    time = datetime.time(int(hour), int(minute), int(sec))

    return time, nsec


def _parse_date_timestamp(date):
    """Parse timestamp string in nanoseconds from epoch.

    This matches 1418423383802588035.

    Args:
        date (str): the date string to be parsed.

    Returns:
        A tuple of the format (date_time, nsec), where date_time is a
        datetime.datetime object and nsec is an int of the remaining
        nanoseconds.

    Raises:
        ValueError: if the date format does not match.
    """
    pattern = re.compile(r'^\d+$')

    if not pattern.match(date):
        raise ValueError('Wrong date format: {}'.format(date))

    timestamp_ns = int(date)

    date_time = datetime.datetime.fromtimestamp(
        timestamp_ns // NSEC_PER_SEC
    )
    # Set the microseconds to 0 because values < 1 second are covered
    # by the nsec value.
    date_time = date_time.replace(microsecond=0)
    nsec = timestamp_ns % NSEC_PER_SEC

    return date_time, nsec


def parse_date(date):
    """Try to parse a date string from one of many formats.

    Args:
        date (str): the date string to be parsed.

    Returns:
        A tuple of the format (date_time, nsec), where date_time is
        one of either datetime.datetime or datetime.time, depending on
        whether the date string contains full date information or only
        the time of day. The latter case can still be useful when used
        in conjuction with a trace collection's date to provide the
        missing information. The nsec element of the tuple is an int and
        corresponds to the nanoseconds for the given date/timestamp.
        This is due to datetime objects only supporting a resolution
        down to the microsecond.

    Raises:
        ValueError: if the date does not correspond to any of the
        supported formats.
    """
    parsers = [
        _parse_date_full_with_nsec, _parse_date_full,
        _parse_date_time_with_nsec, _parse_date_time,
        _parse_date_timestamp
    ]

    date_time = None
    nsec = None

    for parser in parsers:
        try:
            (date_time, nsec) = parser(date)
        except ValueError:
            continue

        # If no exception was raised, the parser found a match, so
        # stop iterating
        break

    if date_time is None or nsec is None:
        # None of the parsers were a match
        raise ValueError('Unrecognised date format: {}'.format(date))

    return date_time, nsec


def parse_trace_collection_date(collection, date, gmt=False, handles=None):
    """Parse a date string, using a trace collection to disambiguate
    incomplete dates.

    Args:
        collection (TraceCollection): a babeltrace TraceCollection
        instance.

        handles (TraceHandle): a babeltrace TraceHandle instance.

        date (string): the date string to be parsed.

        gmt (bool, optional): flag indicating whether the timestamp is
        in the local timezone or gmt (default: False).

    Returns:
        A timestamp (int) in nanoseconds since epoch, corresponding to
        the parsed date.

    Raises:
        ValueError: if the date format is unrecognised, or if the date
        format does not specify the date and the trace collection spans
        multiple days.
    """
    try:
        date_time, nsec = parse_date(date)
    except ValueError:
        # This might raise ValueError if the date is in an invalid
        # format, so just re-raise the exception to inform the caller
        # of the problem.
        raise

    # date_time will either be an actual datetime.datetime object, or
    # just a datetime.time object, depending on the format. In the
    # latter case, try and fill out the missing date information from
    # the trace collection's date.
    if isinstance(date_time, datetime.time):
        try:
            collection_date = trace_utils.get_trace_collection_date(collection,
                                                                    handles)
        except ValueError:
            raise ValueError(
                'Invalid date format for multi-day trace: {}'.format(date)
            )

        date_time = datetime.datetime.combine(collection_date, date_time)

    if gmt:
        date_time = date_time + datetime.timedelta(seconds=timezone)

    timestamp_ns = int(date_time.timestamp()) * NSEC_PER_SEC + nsec

    return timestamp_ns


def parse_trace_collection_time_range(collection, time_range,
                                      gmt=False, handles=None):
    """Parse a time range string, using a trace collection to
    disambiguate incomplete dates.

    Args:
        collection (TraceCollection): a babeltrace TraceCollection
        instance.

        handles (TraceHandle): a babeltrace TraceHandle instance.

        time_range (string): the time range string to be parsed.

        gmt (bool, optional): flag indicating whether the timestamps are
        in the local timezone or gmt (default: False).

    Returns:
        A tuple (begin, end) of the two timestamps (int) in nanoseconds
        since epoch, corresponding to the parsed dates.

    Raises:
        ValueError: if the time range or date format is unrecognised,
        or if the date format does not specify the date and the trace
        collection spans multiple days.
    """
    pattern = re.compile(r'^\[(?P<begin>.*),(?P<end>.*)\]$')
    if not pattern.match(time_range):
        raise ValueError('Invalid time range format: {}'.format(time_range))

    begin_str = pattern.search(time_range).group('begin').strip()
    end_str = pattern.search(time_range).group('end').strip()

    try:
        begin = parse_trace_collection_date(collection, begin_str,
                                            gmt, handles)
        end = parse_trace_collection_date(collection, end_str, gmt, handles)
    except ValueError:
        # Either of the dates was in the wrong format, propagate the
        # exception to the caller.
        raise

    return begin, end
