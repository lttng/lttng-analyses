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

from .analysis_test import AnalysisTest


class CpuTest(AnalysisTest):
    def write_trace(self):
        # runs the whole time: 100%
        self.trace_writer.write_sched_switch(1000, 5, 'swapper/5',
                                             0, 'prog100pc-cpu5', 42)
        # runs for 2s alternating with swapper out every 100ms
        self.trace_writer.sched_switch_50pc(1100, 5000, 0, 100, 'swapper/0',
                                            0, 'prog20pc-cpu0', 30664)
        # runs for 2.5s alternating with swapper out every 100ms
        self.trace_writer.sched_switch_50pc(5100, 10000, 1, 100, 'swapper/1',
                                            0, 'prog25pc-cpu1', 30665)
        # switch out prog100pc-cpu5
        self.trace_writer.write_sched_switch(11000, 5, 'prog100pc-cpu5',
                                             42, 'swapper/5', 0)
        self.trace_writer.flush()

    def test_cputop(self):
        test_name = 'cputop'
        expected = self.get_expected_output(test_name)
        result = self.get_cmd_output('lttng-cputop',
                                     options='--no-intersection')

        self._assertMultiLineEqual(result, expected, test_name)
