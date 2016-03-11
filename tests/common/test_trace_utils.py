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

import unittest
from datetime import date
from lttnganalyses.common import trace_utils


# Mock of babeltrace's TraceCollection, used to test date methods
class TraceCollection():
    def __init__(self, begin_ts, end_ts):
        self.begin_ts = begin_ts
        self.end_ts = end_ts

    @property
    def timestamp_begin(self):
        return self.begin_ts

    @property
    def timestamp_end(self):
        return self.end_ts


class TestIsMultiDayTraceCollection(unittest.TestCase):
    def test_same_day(self):
        begin_ts = 683153828123456789
        # 1 hour later
        end_ts = 683157428123456789
        collection = TraceCollection(begin_ts, end_ts)
        result = trace_utils.is_multi_day_trace_collection(collection)

        self.assertFalse(result)

    def test_different_day(self):
        begin_ts = 683153828123456789
        # 24 hours later
        end_ts = 683240228123456789
        collection = TraceCollection(begin_ts, end_ts)
        result = trace_utils.is_multi_day_trace_collection(collection)

        self.assertTrue(result)


class TestGetTraceCollectionDate(unittest.TestCase):
    def test_single_day(self):
        begin_ts = 683153828123456789
        # 1 hour later
        end_ts = 683157428123456789
        collection = TraceCollection(begin_ts, end_ts)
        result = trace_utils.get_trace_collection_date(collection)
        expected = date(1991, 8, 25)

        self.assertEqual(result, expected)

    def test_multi_day(self):
        begin_ts = 683153828123456789
        # 24 hours later
        end_ts = 683240228123456789
        collection = TraceCollection(begin_ts, end_ts)

        self.assertRaises(ValueError, trace_utils.get_trace_collection_date,
                          collection)


class TestGetSyscallName(unittest.TestCase):
    class Event():
        def __init__(self, name):
            self.name = name

    def test_sys(self):
        event = self.Event('sys_open')
        result = trace_utils.get_syscall_name(event)

        self.assertEqual(result, 'open')

    def test_syscall_entry(self):
        event = self.Event('syscall_entry_open')
        result = trace_utils.get_syscall_name(event)

        self.assertEqual(result, 'open')

    def test_not_syscall(self):
        event = self.Event('whatever')

        self.assertRaises(ValueError, trace_utils.get_syscall_name, event)
