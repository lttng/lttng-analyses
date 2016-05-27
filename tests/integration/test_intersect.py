# The MIT License (MIT)
#
# Copyright (C) 2016 - Julien Desfossez <jdesfossez@efficios.com>
#                      Antoine Busque <abusque@efficios.com>
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
from lttnganalyses.common import trace_utils
from .analysis_test import AnalysisTest


class IntersectTest(AnalysisTest):
    def write_trace(self):
        # Write these events in the default stream.
        self.trace_writer.write_softirq_raise(1005, 3, 1)
        self.trace_writer.write_softirq_entry(1006, 3, 1)
        self.trace_writer.write_softirq_exit(1009, 3, 1)

        # Override the default stream, so all new events are written
        # in a different stream, no overlapping timestamps between streams.
        self.trace_writer.create_stream()
        self.trace_writer.write_softirq_exit(1010, 2, 7)
        self.trace_writer.flush()

    @unittest.skipIf(trace_utils.read_babeltrace_version() <
                     trace_utils.BT_INTERSECT_VERSION,
                     "not supported by Babeltrace < %s" %
                     trace_utils.BT_INTERSECT_VERSION,)
    def test_no_intersection(self):
        test_name = 'no_intersection'
        expected = self.get_expected_output(test_name)
        result = self.get_cmd_output('lttng-irqstats')

        self._assertMultiLineEqual(result, expected, test_name)

    def test_disable_intersect(self):
        test_name = 'disable_intersect'
        expected = self.get_expected_output(test_name)
        result = self.get_cmd_output('lttng-irqstats',
                                     options='--no-intersection')

        self._assertMultiLineEqual(result, expected, test_name)
