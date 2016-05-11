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
from lttnganalyses.core import stats
from lttnganalyses.common import format_utils
from .utils import TimezoneUtils


class TestFormatSize(unittest.TestCase):
    def test_negative(self):
        self.assertRaises(ValueError, format_utils.format_size, -1)

    def test_zero(self):
        result = format_utils.format_size(0)
        result_decimal = format_utils.format_size(0, binary_prefix=False)

        self.assertEqual(result, '0   B')
        self.assertEqual(result_decimal, '0  B')

    def test_huge(self):
        # 2000 YiB or 2475.88 YB
        huge_value = 2417851639229258349412352000
        result = format_utils.format_size(huge_value)
        result_decimal = format_utils.format_size(huge_value,
                                                  binary_prefix=False)

        self.assertEqual(result, '2000.00 YiB')
        self.assertEqual(result_decimal, '2417.85 YB')

    def test_reasonable(self):
        # 2 GB or 1.86 GiB
        reasonable_value = 2000000000
        result = format_utils.format_size(reasonable_value)
        result_decimal = format_utils.format_size(reasonable_value,
                                                  binary_prefix=False)

        self.assertEqual(result, '1.86 GiB')
        self.assertEqual(result_decimal, '2.00 GB')


class TestFormatPrioList(unittest.TestCase):
    def test_empty(self):
        prio_list = []
        result = format_utils.format_prio_list(prio_list)

        self.assertEqual(result, '[]')

    def test_one_prio(self):
        prio_list = [stats.PrioEvent(0, 0)]
        result = format_utils.format_prio_list(prio_list)

        self.assertEqual(result, '[0]')

    def test_multiple_prios(self):
        prio_list = [stats.PrioEvent(0, 0), stats.PrioEvent(0, 1)]
        result = format_utils.format_prio_list(prio_list)

        self.assertEqual(result, '[0, 1]')

    def test_repeated_prio(self):
        prio_list = [stats.PrioEvent(0, 0), stats.PrioEvent(0, 0)]
        result = format_utils.format_prio_list(prio_list)

        self.assertEqual(result, '[0 (2 times)]')

    def test_repeated_prios(self):
        prio_list = [
            stats.PrioEvent(0, 0), stats.PrioEvent(0, 1),
            stats.PrioEvent(0, 0), stats.PrioEvent(0, 1)
        ]
        result = format_utils.format_prio_list(prio_list)

        self.assertEqual(result, '[0 (2 times), 1 (2 times)]')


class TestFormatTimestamp(unittest.TestCase):
    # This may or may not be the time of the Linux 0.0.1 announcement.
    ARBITRARY_TIMESTAMP = 683153828123456789

    def setUp(self):
        self.tz_utils = TimezoneUtils()
        self.tz_utils.set_up_timezone()

    def tearDown(self):
        self.tz_utils.tear_down_timezone()

    def test_time(self):
        result = format_utils.format_timestamp(self.ARBITRARY_TIMESTAMP)
        result_gmt = format_utils.format_timestamp(
            self.ARBITRARY_TIMESTAMP, gmt=True
        )

        self.assertEqual(result, '16:57:08.123456789')
        self.assertEqual(result_gmt, '20:57:08.123456789')

    def test_date(self):
        result = format_utils.format_timestamp(
            self.ARBITRARY_TIMESTAMP, print_date=True
        )
        result_gmt = format_utils.format_timestamp(
            self.ARBITRARY_TIMESTAMP, print_date=True, gmt=True
        )

        self.assertEqual(result, '1991-08-25 16:57:08.123456789')
        self.assertEqual(result_gmt, '1991-08-25 20:57:08.123456789')

    def test_negative(self):
        # Make sure the time module handles pre-epoch dates correctly
        result = format_utils.format_timestamp(
            -self.ARBITRARY_TIMESTAMP, print_date=True
        )
        result_gmt = format_utils.format_timestamp(
            -self.ARBITRARY_TIMESTAMP, print_date=True, gmt=True
        )

        self.assertEqual(result, '1948-05-08 23:02:51.876543211')
        self.assertEqual(result_gmt, '1948-05-09 03:02:51.876543211')


class TestFormatTimeRange(unittest.TestCase):
    BEGIN_TS = 683153828123456789
    # 1 hour later
    END_TS = 683157428123456789

    def _mock_format_timestamp(self, timestamp, print_date, gmt):
        date_str = '1991-08-25 '

        if timestamp == TestFormatTimeRange.BEGIN_TS:
            if gmt:
                time_str = '20:57:08.123456789'
            else:
                time_str = '16:57:08.123456789'
        elif timestamp == TestFormatTimeRange.END_TS:
            if gmt:
                time_str = '21:57:08.123456789'
            else:
                time_str = '17:57:08.123456789'

        if print_date:
            return date_str + time_str
        else:
            return time_str

    def setUp(self):
        self._original_format_timestamp = format_utils.format_timestamp
        format_utils.format_timestamp = self._mock_format_timestamp

    def tearDown(self):
        format_utils.format_timestamp = self._original_format_timestamp

    def test_time_only(self):
        result = format_utils.format_time_range(
            self.BEGIN_TS, self.END_TS
        )
        result_gmt = format_utils.format_time_range(
            self.BEGIN_TS, self.END_TS, gmt=True
        )

        self.assertEqual(result,
                         '[16:57:08.123456789, 17:57:08.123456789]')
        self.assertEqual(result_gmt,
                         '[20:57:08.123456789, 21:57:08.123456789]')

    def test_print_date(self):
        result = format_utils.format_time_range(
            self.BEGIN_TS, self.END_TS, print_date=True
        )
        result_gmt = format_utils.format_time_range(
            self.BEGIN_TS, self.END_TS, print_date=True, gmt=True
        )

        self.assertEqual(
            result,
            '[1991-08-25 16:57:08.123456789, 1991-08-25 17:57:08.123456789]'
        )
        self.assertEqual(
            result_gmt,
            '[1991-08-25 20:57:08.123456789, 1991-08-25 21:57:08.123456789]'
        )


class TestFormatIpv4(unittest.TestCase):
    IP_INTEGER = 0x7f000001
    IP_SEQUENCE = [127, 0, 0, 1]

    def test_integer(self):
        result = format_utils.format_ipv4(self.IP_INTEGER)

        self.assertEqual(result, '127.0.0.1')

    def test_sequence(self):
        result = format_utils.format_ipv4(self.IP_SEQUENCE)

        self.assertEqual(result, '127.0.0.1')

    def test_with_port(self):
        result = format_utils.format_ipv4(self.IP_SEQUENCE, port=8080)

        self.assertEqual(result, '127.0.0.1:8080')
