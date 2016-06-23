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
import unittest
from lttnganalyses.common import parse_utils
from .utils import TimezoneUtils


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


class TestParseSize(unittest.TestCase):
    def test_garbage(self):
        self.assertRaises(ValueError, parse_utils.parse_size,
                          'ceci n\'est pas une size')
        self.assertRaises(ValueError, parse_utils.parse_size,
                          '12.34.56')

    def test_invalid_units(self):
        self.assertRaises(ValueError, parse_utils.parse_size, '500 furlongs')

    def test_binary_units(self):
        result = parse_utils.parse_size('500 KiB')
        self.assertEqual(result, 512000)
        result = parse_utils.parse_size('-500 KiB')
        self.assertEqual(result, -512000)
        # no space left between units and value is intentional
        result = parse_utils.parse_size('0.01MiB')
        self.assertEqual(result, 10485)
        result = parse_utils.parse_size('1200 YiB')
        self.assertEqual(result, 1450710983537555009647411200)
        result = parse_utils.parse_size('1234 B')
        self.assertEqual(result, 1234)

    def test_coreutils_units(self):
        result = parse_utils.parse_size('500 K')
        self.assertEqual(result, 512000)
        result = parse_utils.parse_size('-500 K')
        self.assertEqual(result, -512000)
        # no space left between units and value is intentional
        result = parse_utils.parse_size('0.01M')
        self.assertEqual(result, 10485)
        result = parse_utils.parse_size('1200 Y')
        self.assertEqual(result, 1450710983537555009647411200)

    def test_si_units(self):
        result = parse_utils.parse_size('500 KB')
        self.assertEqual(result, 500000)
        result = parse_utils.parse_size('-500 KB')
        self.assertEqual(result, -500000)
        # no space left between units and value is intentional
        result = parse_utils.parse_size('0.01MB')
        self.assertEqual(result, 10000)
        result = parse_utils.parse_size('40 ZB')
        self.assertEqual(result, 40000000000000000000000)
        # Sizes a bit larger than 40 ZB (e.g. 50 ZB and up) with
        # decimal units don't get parsed quite as precisely because of
        # the nature of floating point numbers. If precision is needed
        # for larger values with these units, it could be fixed, but
        # for now it seems unlikely so we leave it as is

    def test_no_units(self):
        result = parse_utils.parse_size('1234')
        self.assertEqual(result, 1234)
        result = parse_utils.parse_size('1234.567')
        self.assertEqual(result, 1234)
        result = parse_utils.parse_size('-1234.567')
        self.assertEqual(result, -1234)


class TestParseDuration(unittest.TestCase):
    def test_garbage(self):
        self.assertRaises(ValueError, parse_utils.parse_duration,
                          'ceci n\'est pas une duration')
        self.assertRaises(ValueError, parse_utils.parse_duration,
                          '12.34.56')

    def test_invalid_units(self):
        self.assertRaises(ValueError, parse_utils.parse_duration,
                          '500 furlongs')

    def test_valid_units(self):
        result = parse_utils.parse_duration('1s')
        self.assertEqual(result, 1000000000)
        result = parse_utils.parse_duration('-1s')
        self.assertEqual(result, -1000000000)
        result = parse_utils.parse_duration('1234.56 ms')
        self.assertEqual(result, 1234560000)
        result = parse_utils.parse_duration('1.23 us')
        self.assertEqual(result, 1230)
        result = parse_utils.parse_duration('1.23 µs')
        self.assertEqual(result, 1230)
        result = parse_utils.parse_duration('1234 ns')
        self.assertEqual(result, 1234)
        result = parse_utils.parse_duration('0.001 ns')
        self.assertEqual(result, 0)

    def test_no_units(self):
        result = parse_utils.parse_duration('1234.567')
        self.assertEqual(result, 1234567000000)


class TestParseDate(unittest.TestCase):
    def setUp(self):
        self.tz_utils = TimezoneUtils()
        self.tz_utils.set_up_timezone()

    def tearDown(self):
        self.tz_utils.tear_down_timezone()

    def test_parse_full_date_nsec(self):
        date_expected = datetime.datetime(2014, 12, 12, 17, 29, 43)
        nsec_expected = 802588035
        date, nsec = parse_utils.parse_date('2014-12-12 17:29:43.802588035')
        self.assertEqual(date, date_expected)
        self.assertEqual(nsec, nsec_expected)
        date, nsec = parse_utils.parse_date('2014-12-12T17:29:43.802588035')
        self.assertEqual(date, date_expected)
        self.assertEqual(nsec, nsec_expected)

    def test_parse_full_date(self):
        date_expected = datetime.datetime(2014, 12, 12, 17, 29, 43)
        nsec_expected = 0
        date, nsec = parse_utils.parse_date('2014-12-12 17:29:43')
        self.assertEqual(date, date_expected)
        self.assertEqual(nsec, nsec_expected)
        date, nsec = parse_utils.parse_date('2014-12-12T17:29:43')
        self.assertEqual(date, date_expected)
        self.assertEqual(nsec, nsec_expected)

    def test_parse_time_nsec(self):
        time_expected = datetime.time(17, 29, 43)
        nsec_expected = 802588035
        time, nsec = parse_utils.parse_date('17:29:43.802588035')
        self.assertEqual(time, time_expected)
        self.assertEqual(nsec, nsec_expected)

    def test_parse_time(self):
        time_expected = datetime.time(17, 29, 43)
        nsec_expected = 0
        time, nsec = parse_utils.parse_date('17:29:43')
        self.assertEqual(time, time_expected)
        self.assertEqual(nsec, nsec_expected)

    def test_parse_timestamp(self):
        time_expected = datetime.datetime(2014, 12, 12, 17, 29, 43)
        nsec_expected = 802588035
        date, nsec = parse_utils.parse_date('1418423383802588035')
        self.assertEqual(date, time_expected)
        self.assertEqual(nsec, nsec_expected)

    def test_parse_date_invalid(self):
        self.assertRaises(ValueError, parse_utils.parse_date,
                          'ceci n\'est pas une date')


class TestParseTraceCollectionDate(unittest.TestCase):
    DATE_FULL = '2014-12-12 17:29:43'
    DATE_TIME = '17:29:43'
    SINGLE_DAY_COLLECTION = TraceCollection(
        1418423383802588035, 1418423483802588035
    )
    MULTI_DAY_COLLECTION = TraceCollection(
        1418423383802588035, 1419423383802588035
    )

    def _mock_parse_date(self, date):
        if date == self.DATE_FULL:
            return (datetime.datetime(2014, 12, 12, 17, 29, 43), 0)
        elif date == self.DATE_TIME:
            return (datetime.time(17, 29, 43), 0)
        else:
            raise ValueError('Unrecognised date format: {}'.format(date))

    def setUp(self):
        self.tz_utils = TimezoneUtils()
        self.tz_utils.set_up_timezone()
        self._original_parse_date = parse_utils.parse_date
        parse_utils.parse_date = self._mock_parse_date

    def tearDown(self):
        self.tz_utils.tear_down_timezone()
        parse_utils.parse_date = self._original_parse_date

    def test_invalid_date(self):
        self.assertRaises(
            ValueError, parse_utils.parse_trace_collection_date,
            self.SINGLE_DAY_COLLECTION, 'ceci n\'est pas une date'
        )

    def test_single_day_date(self):
        expected = 1418423383000000000
        result = parse_utils.parse_trace_collection_date(
            self.SINGLE_DAY_COLLECTION, self.DATE_FULL
        )
        self.assertEqual(result, expected)

    def test_single_day_time(self):
        expected = 1418423383000000000
        result = parse_utils.parse_trace_collection_date(
            self.SINGLE_DAY_COLLECTION, self.DATE_TIME
        )
        self.assertEqual(result, expected)

    def test_multi_day_date(self):
        expected = 1418423383000000000
        result = parse_utils.parse_trace_collection_date(
            self.MULTI_DAY_COLLECTION, self.DATE_FULL
        )
        self.assertEqual(result, expected)

    def test_multi_day_time(self):
        self.assertRaises(
            ValueError, parse_utils.parse_trace_collection_date,
            self.MULTI_DAY_COLLECTION, self.DATE_TIME
        )


class TestParseTraceCollectionTimeRange(unittest.TestCase):
    DATE_FULL_BEGIN = '2014-12-12 17:29:43'
    DATE_FULL_END = '2014-12-12 17:29:44'
    DATE_TIME_BEGIN = '17:29:43'
    DATE_TIME_END = '17:29:44'
    EXPECTED_BEGIN = 1418423383000000000
    EXPECTED_END = 1418423384000000000
    SINGLE_DAY_COLLECTION = TraceCollection(
        1418423383802588035, 1418423483802588035
    )
    MULTI_DAY_COLLECTION = TraceCollection(
        1418423383802588035, 1419423383802588035
    )
    TIME_RANGE_FMT = '[{}, {}]'

    def _mock_parse_trace_collection_date(self, collection, date, gmt=False,
                                          handles=None):
        if collection == self.SINGLE_DAY_COLLECTION:
            if date == self.DATE_FULL_BEGIN or date == self.DATE_TIME_BEGIN:
                timestamp = 1418423383000000000
            elif date == self.DATE_FULL_END or date == self.DATE_TIME_END:
                timestamp = 1418423384000000000
            else:
                raise ValueError('Unrecognised date format: {}'.format(date))
        elif collection == self.MULTI_DAY_COLLECTION:
            if date == self.DATE_FULL_BEGIN:
                timestamp = 1418423383000000000
            elif date == self.DATE_FULL_END:
                timestamp = 1418423384000000000
            elif date == self.DATE_TIME_BEGIN or date == self.DATE_TIME_END:
                raise ValueError(
                    'Invalid date format for multi-day trace: {}'.format(date)
                )
            else:
                raise ValueError('Unrecognised date format: {}'.format(date))

        return timestamp

    def setUp(self):
        self._original_parse_trace_collection_date = (
            parse_utils.parse_trace_collection_date
        )
        parse_utils.parse_trace_collection_date = (
            self._mock_parse_trace_collection_date
        )

    def tearDown(self):
        parse_utils.parse_trace_collection_date = (
            self._original_parse_trace_collection_date
        )

    def test_invalid_format(self):
        self.assertRaises(
            ValueError, parse_utils.parse_trace_collection_time_range,
            self.SINGLE_DAY_COLLECTION, 'ceci n\'est pas un time range'
        )

    def test_single_day_date(self):
        time_range = self.TIME_RANGE_FMT.format(
            self.DATE_FULL_BEGIN, self.DATE_FULL_END
        )
        begin, end = parse_utils.parse_trace_collection_time_range(
            self.SINGLE_DAY_COLLECTION, time_range
        )
        self.assertEqual(begin, self.EXPECTED_BEGIN)
        self.assertEqual(end, self.EXPECTED_END)

    def test_single_day_time(self):
        time_range = self.TIME_RANGE_FMT.format(
            self.DATE_TIME_BEGIN, self.DATE_TIME_END
        )
        begin, end = parse_utils.parse_trace_collection_time_range(
            self.SINGLE_DAY_COLLECTION, time_range
        )
        self.assertEqual(begin, self.EXPECTED_BEGIN)
        self.assertEqual(end, self.EXPECTED_END)

    def test_multi_day_date(self):
        time_range = self.TIME_RANGE_FMT.format(
            self.DATE_FULL_BEGIN, self.DATE_FULL_END
        )
        begin, end = parse_utils.parse_trace_collection_time_range(
            self.MULTI_DAY_COLLECTION, time_range
        )
        self.assertEqual(begin, self.EXPECTED_BEGIN)
        self.assertEqual(end, self.EXPECTED_END)

    def test_multi_day_time(self):
        time_range = self.TIME_RANGE_FMT.format(
            self.DATE_TIME_BEGIN, self.DATE_TIME_END
        )
        self.assertRaises(
            ValueError, parse_utils.parse_trace_collection_time_range,
            self.MULTI_DAY_COLLECTION, time_range
        )
