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


class IrqTest(AnalysisTest):
    def write_trace(self):
        self.trace_writer.write_softirq_raise(1000, 1, 1)
        self.trace_writer.write_softirq_raise(1001, 3, 1)
        self.trace_writer.write_softirq_raise(1002, 1, 9)
        self.trace_writer.write_softirq_exit(1003, 0, 4)
        self.trace_writer.write_softirq_raise(1004, 3, 9)
        self.trace_writer.write_softirq_raise(1005, 3, 7)
        self.trace_writer.write_softirq_entry(1006, 3, 1)
        self.trace_writer.write_softirq_entry(1007, 1, 1)
        self.trace_writer.write_softirq_exit(1008, 1, 1)
        self.trace_writer.write_softirq_exit(1009, 3, 1)
        self.trace_writer.write_softirq_entry(1010, 1, 9)
        self.trace_writer.write_softirq_entry(1011, 3, 7)
        self.trace_writer.write_softirq_exit(1012, 1, 9)
        self.trace_writer.write_softirq_exit(1013, 3, 7)
        self.trace_writer.write_softirq_entry(1014, 3, 9)
        self.trace_writer.write_softirq_exit(1015, 3, 9)
        self.trace_writer.write_irq_handler_entry(1016, 0, 41, 'ahci')
        self.trace_writer.write_softirq_raise(1017, 0, 4)
        self.trace_writer.write_irq_handler_exit(1018, 0, 41, 1)
        self.trace_writer.write_softirq_entry(1019, 0, 4)
        self.trace_writer.write_softirq_exit(1020, 0, 4)
        self.trace_writer.write_irq_handler_entry(1021, 0, 41, 'ahci')
        self.trace_writer.write_softirq_raise(1022, 0, 4)
        self.trace_writer.write_irq_handler_exit(1023, 0, 41, 1)
        self.trace_writer.write_softirq_entry(1024, 0, 4)
        self.trace_writer.write_softirq_exit(1025, 0, 4)
        self.trace_writer.write_irq_handler_entry(1026, 0, 41, 'ahci')
        self.trace_writer.write_softirq_raise(1027, 0, 4)
        self.trace_writer.write_irq_handler_exit(1028, 0, 41, 1)
        self.trace_writer.write_softirq_entry(1029, 0, 4)
        self.trace_writer.write_softirq_exit(1030, 0, 4)
        self.trace_writer.write_irq_handler_entry(1031, 0, 41, 'ahci')
        self.trace_writer.write_softirq_raise(1032, 0, 4)
        self.trace_writer.write_irq_handler_exit(1033, 0, 41, 1)
        self.trace_writer.write_softirq_entry(1034, 0, 4)
        self.trace_writer.write_softirq_exit(1035, 0, 4)
        self.trace_writer.write_irq_handler_entry(1036, 0, 41, 'ahci')
        self.trace_writer.write_softirq_raise(1037, 0, 4)
        self.trace_writer.write_irq_handler_exit(1038, 0, 41, 1)
        self.trace_writer.write_softirq_entry(1039, 0, 4)
        self.trace_writer.write_softirq_exit(1040, 0, 4)
        self.trace_writer.write_irq_handler_entry(1041, 0, 41, 'ahci')
        self.trace_writer.write_softirq_raise(1042, 0, 4)
        self.trace_writer.write_irq_handler_exit(1043, 0, 41, 1)
        self.trace_writer.write_softirq_entry(1044, 0, 4)
        self.trace_writer.write_softirq_exit(1045, 0, 4)
        self.trace_writer.flush()

    def test_irqstats(self):
        expected = self.get_expected_output('irqstats.txt')
        result = self.get_cmd_output('lttng-irqstats')

        self.assertMultiLineEqual(result, expected)

    def test_irqlog(self):
        expected = self.get_expected_output('irqlog.txt')
        result = self.get_cmd_output('lttng-irqlog')

        self.assertMultiLineEqual(result, expected)
