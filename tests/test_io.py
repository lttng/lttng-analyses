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


class IoTest(AnalysisTest):
    def write_trace(self):
        # app (99) is known at statedump
        self.trace_writer.write_lttng_statedump_process_state(
            1000, 0, 99, 99, 99, 99, 98, 98, 'app', 0, 5, 0, 5, 0)
        # app2 (100) unknown at statedump has testfile, FD 3 defined at
        # statedump
        self.trace_writer.write_lttng_statedump_file_descriptor(
            1001, 0, 100, 3, 0, 0, 'testfile')
        # app write 10 bytes to FD 4
        self.trace_writer.write_sched_switch(1002, 0, 'swapper/0', 0, 'app',
                                             99)
        self.trace_writer.write_syscall_write(1004, 0, 1, 4, 0xabcd, 10, 10)
        # app2 reads 100 bytes in FD 3
        self.trace_writer.write_sched_switch(1006, 0, 'app', 99, 'app2', 100)
        self.trace_writer.write_syscall_read(1008, 0, 1, 3, 0xcafe, 100, 100)
        # app3 and its FD 3 are completely unknown at statedump, tries to read
        # 100 bytes from FD 3 but only gets 42
        self.trace_writer.write_sched_switch(1010, 0, 'app2', 100, 'app3', 101)
        self.trace_writer.write_syscall_read(1012, 0, 1, 3, 0xcafe, 100, 42)
        # block write
        self.trace_writer.write_block_rq_issue(1015, 0, 264241152, 33, 10, 40,
                                               99, 0, 0, '', 'app')
        self.trace_writer.write_block_rq_complete(1016, 0, 264241152, 33, 10,
                                                  0, 0, 0, '')
        # block read
        self.trace_writer.write_block_rq_issue(1017, 0, 8388608, 33, 20, 90,
                                               101, 1, 0, '', 'app3')
        self.trace_writer.write_block_rq_complete(1018, 0, 8388608, 33, 20, 0,
                                                  1, 0, '')
        # net xmit
        self.trace_writer.write_net_dev_xmit(1020, 2, 0xff, 32, 100, 'wlan0')
        # net receive
        self.trace_writer.write_netif_receive_skb(1021, 1, 0xff, 100, 'wlan1')
        self.trace_writer.write_netif_receive_skb(1022, 1, 0xff, 200, 'wlan0')
        # syscall open
        self.trace_writer.write_syscall_open(1023, 0, 1, 'test/open/file', 0,
                                             0, 42)
        self.trace_writer.flush()

    def test_iousagetop(self):
        test_name = 'iousagetop'
        expected = self.get_expected_output(test_name)
        result = self.get_cmd_output('lttng-iousagetop')

        self._assertMultiLineEqual(result, expected, test_name)

    def test_iolatencytop(self):
        test_name = 'iolatencytop'
        expected = self.get_expected_output(test_name)
        result = self.get_cmd_output('lttng-iolatencytop')

        self._assertMultiLineEqual(result, expected, test_name)
