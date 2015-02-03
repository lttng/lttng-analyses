#!/usr/bin/env python3
#
# The MIT License (MIT)
#
# Copyright (C) 2015 - Julien Desfossez <jdesfosez@efficios.com>
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
import re
import time
import datetime
import socket
import struct
import sys
from linuxautomaton import sv

NSEC_PER_SEC = 1000000000
MSEC_PER_NSEC = 1000000

O_CLOEXEC = 0o2000000


# imported from include/linux/kdev_t.h
def kdev_major_minor(dev):
    MINORBITS = 20
    MINORMASK = ((1 << MINORBITS) - 1)
    major = dev >> MINORBITS
    minor = dev & MINORMASK
    return "(%d,%d)" % (major, minor)


def get_disk(dev, disks):
    if dev not in disks:
        d = sv.Disk()
        d.name = "%d" % dev
        d.prettyname = kdev_major_minor(dev)
        disks[dev] = d
    else:
        d = disks[dev]
    return d


def convert_size(size, padding_after=False, padding_before=False):
    if padding_after and size < 1024:
        space_after = " "
    else:
        space_after = ""
    if padding_before and size < 1024:
        space_before = " "
    else:
        space_before = ""
    if size <= 0:
        return "0 " + space_before + "B" + space_after
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size, 1024)))
    p = math.pow(1024, i)
    s = round(size/p, 2)
    if (s > 0):
        try:
            v = "%0.02f" % s
            return '%s %s%s%s' % (v, space_before, size_name[i], space_after)
        except:
            print(i, size_name)
            raise Exception("Too big to be true")
    else:
        return '0 B'


def is_multi_day_trace_collection(handle):
    y = m = d = -1
    for h in handle.values():
        if y == -1:
            y = time.localtime(h.timestamp_begin/NSEC_PER_SEC).tm_year
            m = time.localtime(h.timestamp_begin/NSEC_PER_SEC).tm_mon
            d = time.localtime(h.timestamp_begin/NSEC_PER_SEC).tm_mday
        _y = time.localtime(h.timestamp_end/NSEC_PER_SEC).tm_year
        _m = time.localtime(h.timestamp_end/NSEC_PER_SEC).tm_mon
        _d = time.localtime(h.timestamp_end/NSEC_PER_SEC).tm_mday
        if y != _y:
            return True
        elif m != _m:
            return True
        elif d != _d:
            return True
    return False


def trace_collection_date(handle):
    if is_multi_day_trace_collection(handle):
        return None
    for h in handle.values():
        y = time.localtime(h.timestamp_begin/NSEC_PER_SEC).tm_year
        m = time.localtime(h.timestamp_begin/NSEC_PER_SEC).tm_mon
        d = time.localtime(h.timestamp_begin/NSEC_PER_SEC).tm_mday
        return (y, m, d)


def extract_timerange(handle, timerange, gmt):
    p = re.compile('^\[(?P<begin>.*),(?P<end>.*)\]$')
    if not p.match(timerange):
        return None
    b = p.search(timerange).group("begin").strip()
    e = p.search(timerange).group("end").strip()
    begin = date_to_epoch_nsec(handle, b, gmt)
    if begin is None:
        return (None, None)
    end = date_to_epoch_nsec(handle, e, gmt)
    if end is None:
        return (None, None)
    return (begin, end)


def date_to_epoch_nsec(handle, date, gmt):
    # match 2014-12-12 17:29:43.802588035 or 2014-12-12T17:29:43.802588035
    p1 = re.compile('^(?P<year>\d\d\d\d)-(?P<mon>[01]\d)-'
                    '(?P<day>[0123]\d)[\sTt]'
                    '(?P<hour>\d\d):(?P<min>\d\d):(?P<sec>\d\d).'
                    '(?P<nsec>\d\d\d\d\d\d\d\d\d)$')
    # match 2014-12-12 17:29:43 or 2014-12-12T17:29:43
    p2 = re.compile('^(?P<year>\d\d\d\d)-(?P<mon>[01]\d)-'
                    '(?P<day>[0123]\d)[\sTt]'
                    '(?P<hour>\d\d):(?P<min>\d\d):(?P<sec>\d\d)$')
    # match 17:29:43.802588035
    p3 = re.compile('^(?P<hour>\d\d):(?P<min>\d\d):(?P<sec>\d\d).'
                    '(?P<nsec>\d\d\d\d\d\d\d\d\d)$')
    # match 17:29:43
    p4 = re.compile('^(?P<hour>\d\d):(?P<min>\d\d):(?P<sec>\d\d)$')

    if p1.match(date):
        year = p1.search(date).group("year")
        month = p1.search(date).group("mon")
        day = p1.search(date).group("day")
        hour = p1.search(date).group("hour")
        minute = p1.search(date).group("min")
        sec = p1.search(date).group("sec")
        nsec = p1.search(date).group("nsec")
    elif p2.match(date):
        year = p2.search(date).group("year")
        month = p2.search(date).group("mon")
        day = p2.search(date).group("day")
        hour = p2.search(date).group("hour")
        minute = p2.search(date).group("min")
        sec = p2.search(date).group("sec")
        nsec = 0
    elif p3.match(date):
        d = trace_collection_date(handle)
        if d is None:
            print("Use the format 'yyyy-mm-dd hh:mm:ss[.nnnnnnnnn]' "
                  "for multi-day traces")
            return None
        year = d[0]
        month = d[1]
        day = d[2]
        hour = p3.search(date).group("hour")
        minute = p3.search(date).group("min")
        sec = p3.search(date).group("sec")
        nsec = p3.search(date).group("nsec")
    elif p4.match(date):
        d = trace_collection_date(handle)
        if d is None:
            print("Use the format 'yyyy-mm-dd hh:mm:ss[.nnnnnnnnn]' "
                  "for multi-day traces")
            return None
        year = d[0]
        month = d[1]
        day = d[2]
        hour = p4.search(date).group("hour")
        minute = p4.search(date).group("min")
        sec = p4.search(date).group("sec")
        nsec = 0
    else:
        return None

    d = datetime.datetime(int(year), int(month), int(day), int(hour),
                          int(minute), int(sec))
    if gmt:
        d = d + datetime.timedelta(seconds=time.timezone)
    return int(d.timestamp()) * NSEC_PER_SEC + int(nsec)


def process_date_args(command):
    command._arg_multi_day = is_multi_day_trace_collection(command._handle)
    if command._arg_timerange:
        (command._arg_begin, command._arg_end) = \
            extract_timerange(command._handle, command._arg_timerange,
                              command._arg_gmt)
        if command._arg_begin is None or command._arg_end is None:
            print("Invalid timeformat")
            sys.exit(1)
    else:
        if command._arg_begin:
            command._arg_begin = date_to_epoch_nsec(command._handle,
                                                    command._arg_begin,
                                                    command._arg_gmt)
            if command._arg_begin is None:
                print("Invalid timeformat")
                sys.exit(1)
        if command._arg_end:
            command._arg_end = date_to_epoch_nsec(command._handle,
                                                  command._arg_end,
                                                  command._arg_gmt)
            if command._arg_end is None:
                print("Invalid timeformat")
                sys.exit(1)


def ns_to_asctime(ns):
    return time.asctime(time.localtime(ns/NSEC_PER_SEC))


def ns_to_hour(ns):
    d = time.localtime(ns/NSEC_PER_SEC)
    return "%02d:%02d:%02d" % (d.tm_hour, d.tm_min, d.tm_sec)


def ns_to_hour_nsec(ns, multi_day=False, gmt=False):
    if gmt:
        d = time.gmtime(ns/NSEC_PER_SEC)
    else:
        d = time.localtime(ns/NSEC_PER_SEC)
    if multi_day:
        return "%04d-%02d-%02d %02d:%02d:%02d.%09d" % (d.tm_year, d.tm_mon,
                                                       d.tm_mday, d.tm_hour,
                                                       d.tm_min, d.tm_sec,
                                                       ns % NSEC_PER_SEC)
    else:
        return "%02d:%02d:%02d.%09d" % (d.tm_hour, d.tm_min, d.tm_sec,
                                        ns % NSEC_PER_SEC)


def ns_to_sec(ns):
    return "%lu.%09u" % (ns/NSEC_PER_SEC, ns % NSEC_PER_SEC)


def ns_to_day(ns):
    d = time.localtime(ns/NSEC_PER_SEC)
    return "%04d-%02d-%02d" % (d.tm_year, d.tm_mon, d.tm_mday)


def sec_to_hour(ns):
    d = time.localtime(ns)
    return "%02d:%02d:%02d" % (d.tm_hour, d.tm_min, d.tm_sec)


def sec_to_nsec(sec):
    return sec * NSEC_PER_SEC


def seq_to_ipv4(ip):
    return "{}.{}.{}.{}".format(ip[0], ip[1], ip[2], ip[3])


def int_to_ipv4(ip):
    return socket.inet_ntoa(struct.pack("!I", ip))


def str_to_bytes(value):
    num = ""
    unit = ""
    for i in value:
        if i.isdigit() or i == ".":
            num = num + i
        elif i.isalnum():
            unit = unit + i
    num = float(num)
    if len(unit) == 0:
        return int(num)
    if unit in ["B"]:
        return int(num)
    if unit in ["k", "K", "kB", "KB"]:
        return int(num * 1024)
    if unit in ["m", "M", "mB", "MB"]:
        return int(num * 1024 * 1024)
    if unit in ["g", "G", "gB", "GB"]:
        return int(num * 1024 * 1024 * 1024)
    if unit in ["t", "T", "tB", "TB"]:
        return int(num * 1024 * 1024 * 1024 * 1024)
    print("Unit", unit, "not understood")
    return None


def get_v4_addr_str(ip):
    # depending on the version of lttng-modules, the v4addr is a
    # string (< 2.6) or sequence (>= 2.6)
    try:
        return seq_to_ipv4(ip)
    except TypeError:
        return int_to_ipv4(ip)
