# The MIT License (MIT)
#
# Copyright (C) 2015 - Julien Desfossez <jdesfossez@efficios.com>
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

import re
import time
import datetime
import socket
import struct

NSEC_PER_SEC = 1000000000
NSEC_PER_MSEC = 1000000
NSEC_PER_USEC = 1000

BYTES_PER_TIB = 1099511627776
BYTES_PER_GIB = 1073741824
BYTES_PER_MIB = 1048576
BYTES_PER_KIB = 1024

O_CLOEXEC = 0o2000000


def get_syscall_name(event):
    name = event.name

    if name.startswith('sys_'):
        # Strip first 4 because sys_ is 4 chars long
        return name[4:]

    # Name begins with syscall_entry_ (14 chars long)
    return name[14:]


def is_multi_day_trace_collection(handles):
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


def trace_collection_date(handles):
    if is_multi_day_trace_collection(handles):
        return None

    for handle in handles.values():
        trace_time = time.localtime(handle.timestamp_begin / NSEC_PER_SEC)
        year = trace_time.tm_year
        month = trace_time.tm_mon
        day = trace_time.tm_mday
        return (year, month, day)


def extract_timerange(handles, timerange, gmt):
    pattern = re.compile(r'^\[(?P<begin>.*),(?P<end>.*)\]$')
    if not pattern.match(timerange):
        return None, None
    begin_str = pattern.search(timerange).group('begin').strip()
    end_str = pattern.search(timerange).group('end').strip()
    begin = date_to_epoch_nsec(handles, begin_str, gmt)
    end = date_to_epoch_nsec(handles, end_str, gmt)
    return (begin, end)


def date_to_epoch_nsec(handles, date, gmt):
    # match 2014-12-12 17:29:43.802588035 or 2014-12-12T17:29:43.802588035
    pattern1 = re.compile(r'^(?P<year>\d{4})-(?P<mon>[01]\d)-'
                          r'(?P<day>[0-3]\d)[\sTt]'
                          r'(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\.'
                          r'(?P<nsec>\d{9})$')
    # match 2014-12-12 17:29:43 or 2014-12-12T17:29:43
    pattern2 = re.compile(r'^(?P<year>\d{4})-(?P<mon>[01]\d)-'
                          r'(?P<day>[0-3]\d)[\sTt]'
                          r'(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})$')
    # match 17:29:43.802588035
    pattern3 = re.compile(r'^(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\.'
                          r'(?P<nsec>\d{9})$')
    # match 17:29:43
    pattern4 = re.compile(r'^(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})$')

    # match 93847238974923874
    pattern5 = re.compile(r'^\d+$')

    if pattern1.match(date):
        year = pattern1.search(date).group('year')
        month = pattern1.search(date).group('mon')
        day = pattern1.search(date).group('day')
        hour = pattern1.search(date).group('hour')
        minute = pattern1.search(date).group('min')
        sec = pattern1.search(date).group('sec')
        nsec = pattern1.search(date).group('nsec')
    elif pattern2.match(date):
        year = pattern2.search(date).group('year')
        month = pattern2.search(date).group('mon')
        day = pattern2.search(date).group('day')
        hour = pattern2.search(date).group('hour')
        minute = pattern2.search(date).group('min')
        sec = pattern2.search(date).group('sec')
        nsec = 0
    elif pattern3.match(date):
        collection_date = trace_collection_date(handles)
        if collection_date is None:
            print("Use the format 'yyyy-mm-dd hh:mm:ss[.nnnnnnnnn]' "
                  "for multi-day traces")
            return None
        (year, month, day) = collection_date
        hour = pattern3.search(date).group('hour')
        minute = pattern3.search(date).group('min')
        sec = pattern3.search(date).group('sec')
        nsec = pattern3.search(date).group('nsec')
    elif pattern4.match(date):
        collection_date = trace_collection_date(handles)
        if collection_date is None:
            print("Use the format 'yyyy-mm-dd hh:mm:ss[.nnnnnnnnn]' "
                  "for multi-day traces")
            return None
        (year, month, day) = collection_date
        hour = pattern4.search(date).group('hour')
        minute = pattern4.search(date).group('min')
        sec = pattern4.search(date).group('sec')
        nsec = 0
    elif pattern5.match(date):
        return int(date)
    else:
        return None

    date_time = datetime.datetime(int(year), int(month), int(day), int(hour),
                                  int(minute), int(sec))
    if gmt:
        date_time = date_time + datetime.timedelta(seconds=time.timezone)
    return int(date_time.timestamp()) * NSEC_PER_SEC + int(nsec)


def ns_to_asctime(ns):
    return time.asctime(time.localtime(ns/NSEC_PER_SEC))


def ns_to_hour(ns):
    date = time.localtime(ns / NSEC_PER_SEC)
    return '%02d:%02d:%02d' % (date.tm_hour, date.tm_min, date.tm_sec)


def ns_to_hour_nsec(ns, multi_day=False, gmt=False):
    if gmt:
        date = time.gmtime(ns / NSEC_PER_SEC)
    else:
        date = time.localtime(ns / NSEC_PER_SEC)
    if multi_day:
        return ('%04d-%02d-%02d %02d:%02d:%02d.%09d' %
                (date.tm_year, date.tm_mon, date.tm_mday, date.tm_hour,
                 date.tm_min, date.tm_sec, ns % NSEC_PER_SEC))
    else:
        return ('%02d:%02d:%02d.%09d' %
                (date.tm_hour, date.tm_min, date.tm_sec, ns % NSEC_PER_SEC))


def ns_to_sec(ns):
    return '%lu.%09u' % (ns / NSEC_PER_SEC, ns % NSEC_PER_SEC)


def ns_to_day(ns):
    date = time.localtime(ns/NSEC_PER_SEC)
    return '%04d-%02d-%02d' % (date.tm_year, date.tm_mon, date.tm_mday)


def sec_to_hour(ns):
    date = time.localtime(ns)
    return '%02d:%02d:%02d' % (date.tm_hour, date.tm_min, date.tm_sec)


def sec_to_nsec(sec):
    return sec * NSEC_PER_SEC


def seq_to_ipv4(ip):
    return '{}.{}.{}.{}'.format(ip[0], ip[1], ip[2], ip[3])


def int_to_ipv4(ip):
    return socket.inet_ntoa(struct.pack('!I', ip))


def size_str_to_bytes(size_str):
    try:
        units_index = next(i for i, c in enumerate(size_str) if c.isalpha())
    except StopIteration:
        # no units found
        units_index = None

    if units_index is not None:
        size = size_str[:units_index]
        units = size_str[units_index:]
    else:
        size = size_str
        units = None

    try:
        size = float(size)
    except ValueError:
        raise ValueError('invalid size: {}'.format(size))

    # no units defaults to bytes
    if units is not None:
        if units in ['t', 'T', 'tB', 'TB']:
            size *= BYTES_PER_TIB
        elif units in ['g', 'G', 'gB', 'GB']:
            size *= BYTES_PER_GIB
        elif units in ['m', 'M', 'mB', 'MB']:
            size *= BYTES_PER_MIB
        elif units in ['k', 'K', 'kB', 'KB']:
            size *= BYTES_PER_KIB
        elif units == 'B':
            # bytes is already the target unit
            pass
        else:
            raise ValueError('unrecognised units: {}'.format(units))

    size = int(size)

    return size


def duration_str_to_ns(duration_str):
    try:
        units_index = next(i for i, c in enumerate(duration_str)
                           if c.isalpha())
    except StopIteration:
        # no units found
        units_index = None

    if units_index is not None:
        duration = duration_str[:units_index]
        units = duration_str[units_index:].lower()
    else:
        duration = duration_str
        units = None

    try:
        duration = float(duration)
    except ValueError:
        raise ValueError('invalid duration: {}'.format(duration))

    if units is not None:
        if units == 's':
            duration *= NSEC_PER_SEC
        elif units == 'ms':
            duration *= NSEC_PER_MSEC
        elif units in ['us', 'µs']:
            duration *= NSEC_PER_USEC
        elif units == 'ns':
            # ns is already the target unit
            pass
        else:
            raise ValueError('unrecognised units: {}'.format(units))
    else:
        # no units defaults to seconds
        duration *= NSEC_PER_SEC

    duration = int(duration)

    return duration


def get_v4_addr_str(ip):
    # depending on the version of lttng-modules, the v4addr is a
    # string (< 2.6) or sequence (>= 2.6)
    try:
        return seq_to_ipv4(ip)
    except TypeError:
        return int_to_ipv4(ip)
