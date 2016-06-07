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

import os
import subprocess
import unittest
from .trace_writer import TraceWriter


class AnalysisTest(unittest.TestCase):
    COMMON_OPTIONS = '--no-color --no-progress --skip-validation --gmt'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rm_trace = True

    def set_up_class(self):
        dirname = os.path.dirname(os.path.realpath(__file__))
        self.data_path = dirname + '/expected/'
        self.maxDiff = None
        self.trace_writer = TraceWriter()
        self.write_trace()

    def tear_down_class(self):
        if self.rm_trace:
            self.trace_writer.rm_trace()

    def write_trace(self):
        raise NotImplementedError

    def run(self, result=None):
        self.set_up_class()
        super().run(result)
        self.tear_down_class()

        return result

    def get_expected_output(self, test_name):
        expected_path = os.path.join(self.data_path, test_name + '.txt')
        with open(expected_path, 'r', encoding='utf-8') as expected_file:
            return expected_file.read()

    def get_cmd_output(self, exec_name, options=''):
        cmd_fmt = './{} {} {} {}'
        cmd = cmd_fmt.format(exec_name, self.COMMON_OPTIONS,
                             options, self.trace_writer.trace_root)
        test_env = os.environ.copy()
        test_env['LC_ALL'] = 'C.UTF-8'

        try:
            output = subprocess.check_output(cmd, shell=True, universal_newlines=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            output = e.output

        if output[-1:] == '\n':
            output = output[:-1]

        return output

    def save_test_result(self, result, test_name):
        result_path = os.path.join(self.trace_writer.trace_root, test_name)
        with open(result_path, 'w', encoding='utf-8') as result_file:
            result_file.write(result)
            self.rm_trace = False

    def _assertMultiLineEqual(self, result, expected, test_name):
        try:
            self.assertMultiLineEqual(result, expected)
        except AssertionError:
            self.save_test_result(result, test_name)
            raise
