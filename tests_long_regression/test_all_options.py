# The MIT License (MIT)
#
# Copyright (C) 2016 - Julien Desfossez <jdesfossez@efficios.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the 'Software'), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import sys
import shutil
import subprocess
import unittest
import tempfile


class _RefTrace():
    def __init__(self, repo_path, name, begin_ts, end_ts, period1,
                 period2):
        # Directory containing all the trace archives
        repo_path = os.path.join(repo_path, "traces")
        # Path of the extracted trace
        self._path = os.path.join(repo_path, name)
        # Name of the trace without the tar.xz suffix
        self._name = name
        # begin_ts is a valid timestamp inside the trace but not the first
        # event.
        # end_ts is a valid timestamp inside the trace but not the last event.
        # Timestamps are in the GMT timezone
        self._begin_ts = begin_ts
        self._end_ts = end_ts
        # Optional period definitions
        self._period1 = period1
        self._period2 = period2

        print('Extracting %s' % name)
        self._extract_trace(repo_path, self._path)

    @property
    def path(self):
        return self._path

    @property
    def name(self):
        return self._name

    @property
    def begin_ts(self):
        return self._begin_ts

    @property
    def end_ts(self):
        return self._end_ts

    @property
    def period1(self):
        return self._period1

    @property
    def period2(self):
        return self._period2

    def _extract_trace(self, repo_path, path):
        subprocess.check_output("tar -C %s -xJf %s.tar.xz" % (
            repo_path, path), shell=True)


class TestAllOptions(unittest.TestCase):
    COMMON_OPTIONS = '--no-color --no-progress --skip-validation --gmt --debug'

    # Get the traces only once for all the tests
    @classmethod
    def setUpClass(cls):
        super(TestAllOptions, cls).setUpClass()
        cls._traces_repo = "https://github.com/lttng/lttng-ref-traces"
        cls._traces_repo_path = tempfile.mkdtemp()
        cls._traces = {}
        cls.get_traces(cls)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._traces_repo_path)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._out_of_scope_ts_begin = '2032-01-01 15:58:26'
        self._out_of_scope_ts_end = '2032-01-10 15:58:27'

    def get_traces(self):
        # This asserts on error, so the test fails
        subprocess.check_output("git clone %s %s" % (
            self._traces_repo, self._traces_repo_path), shell=True)
        self._traces["picotrace"] = _RefTrace(
            self._traces_repo_path, "picotrace",
            "1970-01-01 00:00:01.004000000",
            "1970-01-01 00:00:01.022000000",
            period1='switch : \$evt.\$name == \\"sched_switch\\" : '
                    '\$evt.\$name == \\"sched_switch\\" && '
                    '\$evt.prev_tid == \$begin.\$evt.next_tid && '
                    '\$evt.cpu_id == \$begin.\$evt.cpu_id',
            period2=' : \$evt.\$name == \\"sched_switch\\" : '
                    '\$evt.\$name == \\"sched_switch\\" && '
                    '\$evt.prev_tid == \$begin.\$evt.next_tid && '
                    '\$evt.cpu_id == \$begin.\$evt.cpu_id')

        # Disabled for now since they take far too long to run
        # self._traces["16-cores-rt"] = _RefTrace(
        #    self._traces_repo_path, "16-cores-rt",
        #    "2016-07-20 18:02:05.196332110",
        #    "2016-07-20 18:02:07.282598088",
        #    period1='switch : \$evt.\$name == \\"sched_switch\\" : '
        #            '\$evt.\$name == \\"sched_switch\\" && '
        #            '\$evt.prev_tid == \$begin.\$evt.next_tid && '
        #            '\$evt.cpu_id == \$begin.\$evt.cpu_id',
        #    period2=': \$evt.\$name == \\"sched_switch\\" : '
        #            '\$evt.\$name == \\"sched_switch\\" && '
        #            '\$evt.prev_tid == \$begin.\$evt.next_tid && '
        #            '\$evt.cpu_id == \$begin.\$evt.cpu_id')

    def get_cmd_return(self, exec_name, options):
        cmd_fmt = './{} {} {} {}'

        # Create an utf-8 test env
        test_env = os.environ.copy()
        test_env['LC_ALL'] = 'C.UTF-8'

        for t in self._traces.keys():
            trace = self._traces[t]
            opt = options.replace('$BEGIN_TS$', trace.begin_ts)
            opt = opt.replace('$END_TS$', trace.end_ts)
            opt = opt.replace('$PERIOD1$', trace.period1)
            opt = opt.replace('$PERIOD2$', trace.period2)
            cmd = cmd_fmt.format(exec_name, self.COMMON_OPTIONS, opt,
                                 trace.path)
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, env=test_env)
            output, unused_err = process.communicate()
            msg = 'Cmd: %s\nReturn: %d\nOutput: %s' % (
                cmd, process.returncode,
                output.decode(sys.stderr.encoding))
            self.assertEqual(process.returncode, 0, msg=msg)

        return output

    def run_with_common_options(self, exec_name):
        self.get_cmd_return(exec_name, '')
        self.get_cmd_return(exec_name, '-r 1')
        self.get_cmd_return(exec_name, '--cpu 0')

        # Timestamp handling
        self.get_cmd_return(exec_name, '--begin "$BEGIN_TS$"')
        self.get_cmd_return(exec_name, '--end "$END_TS$"')
        self.get_cmd_return(exec_name, '--begin "$BEGIN_TS$" --end "$END_TS$"')
        self.get_cmd_return(exec_name, '--timerange "[$BEGIN_TS$, $END_TS$]"')
        # Out-of-scope timestamps (empty dataset)
        self.get_cmd_return(exec_name, '--begin "%s"' % (
            self._out_of_scope_ts_begin))
        self.get_cmd_return(exec_name, '--end "%s"' % (
            self._out_of_scope_ts_end))
        self.get_cmd_return(exec_name, '--begin "%s" --end "%s"' % (
                            self._out_of_scope_ts_begin,
                            self._out_of_scope_ts_end))
        self.get_cmd_return(exec_name, '--timerange "[%s,%s]"' % (
                            self._out_of_scope_ts_begin,
                            self._out_of_scope_ts_end))
        self.get_cmd_return(exec_name, '--period "$PERIOD1$"')
        self.get_cmd_return(exec_name, '--period "$PERIOD2$"')
        self.get_cmd_return(exec_name, '--period "$PERIOD1$" '
                                       '--period "$PERIOD2$"')

    def run_with_proc_filter_args(self, exec_name):
        self.get_cmd_return(exec_name, '--tid 0')
        self.get_cmd_return(exec_name, '--procname test')

    def run_with_min_max_args(self, exec_name):
        self.get_cmd_return(exec_name, '--min 0')
        self.get_cmd_return(exec_name, '--max 0')

    def run_with_freq_args(self, exec_name):
        self.get_cmd_return(exec_name, '--freq')
        self.get_cmd_return(exec_name, '--freq-resolution 10')
        self.get_cmd_return(exec_name, '--freq-uniform')
        self.get_cmd_return(exec_name, '--freq-series')

    def run_with_log_args(self, exec_name):
        self.get_cmd_return(exec_name, '--log')

    def run_with_top_args(self, exec_name):
        self.get_cmd_return(exec_name, '--top')
        self.get_cmd_return(exec_name, '--limit 0')

    def run_with_stats_args(self, exec_name):
        self.get_cmd_return(exec_name, '--stats')

    # lttng-cputop
    def test_all_options_cputop(self):
        exec_name = 'lttng-cputop'
        self.run_with_common_options(exec_name)
        self.run_with_proc_filter_args(exec_name)
        self.run_with_top_args(exec_name)

    # lttng-io*
    def run_all_options_io(self, exec_name):
        self.run_with_common_options(exec_name)
        self.run_with_min_max_args(exec_name)
        self.run_with_freq_args(exec_name)
        self.run_with_log_args(exec_name)
        self.run_with_top_args(exec_name)
        self.run_with_stats_args(exec_name)
        self.get_cmd_return(exec_name, '--minsize 0')
        self.get_cmd_return(exec_name, '--maxsize 0')

    def test_all_options_iolatencyfreq(self):
        exec_name = 'lttng-iolatencyfreq'
        self.run_all_options_io(exec_name)

    def test_all_options_iolatencystats(self):
        exec_name = 'lttng-iolatencystats'
        self.run_all_options_io(exec_name)

    def test_all_options_iolatencytop(self):
        exec_name = 'lttng-iolatencytop'
        self.run_all_options_io(exec_name)

    # lttng-irq*
    def run_all_options_irq(self, exec_name):
        self.run_with_common_options(exec_name)
        self.run_with_min_max_args(exec_name)
        self.run_with_freq_args(exec_name)
        self.run_with_log_args(exec_name)
        self.run_with_stats_args(exec_name)
        self.get_cmd_return(exec_name, '--irq 0')
        self.get_cmd_return(exec_name, '--softirq 0')

    def test_all_options_irqfreq(self):
        exec_name = 'lttng-irqfreq'
        self.run_all_options_irq(exec_name)

    def test_all_options_irqlog(self):
        exec_name = 'lttng-irqlog'
        self.run_all_options_irq(exec_name)

    def test_all_options_irqstats(self):
        exec_name = 'lttng-irqstats'
        self.run_all_options_irq(exec_name)

    # lttng-memtop
    def test_all_options_memtop(self):
        exec_name = 'lttng-memtop'
        self.run_with_common_options(exec_name)
        self.run_with_proc_filter_args(exec_name)
        self.run_with_top_args(exec_name)

    # lttng-period*
    def run_all_options_period(self, exec_name):
        self.run_with_common_options(exec_name)
        self.run_with_min_max_args(exec_name)
        self.run_with_freq_args(exec_name)
        self.run_with_log_args(exec_name)
        self.run_with_stats_args(exec_name)
        self.run_with_top_args(exec_name)
        self.get_cmd_return(exec_name, '--total')
        self.get_cmd_return(exec_name, '--per-period')

    def test_all_options_periodfreq(self):
        exec_name = 'lttng-periodfreq'
        self.get_cmd_return(exec_name, '--per-period --freq-uniform')
        self.get_cmd_return(exec_name, '--total --freq-uniform')
        self.run_all_options_period(exec_name)

    def test_all_options_periodlog(self):
        exec_name = 'lttng-periodlog'
        self.run_all_options_period(exec_name)

    def test_all_options_periodstats(self):
        exec_name = 'lttng-periodstats'
        self.run_all_options_period(exec_name)

    def test_all_options_periodtop(self):
        exec_name = 'lttng-periodtop'
        self.run_all_options_period(exec_name)

    # lttng-sched*
    def run_all_options_sched(self, exec_name):
        self.run_with_common_options(exec_name)
        self.run_with_proc_filter_args(exec_name)
        self.run_with_min_max_args(exec_name)
        self.run_with_freq_args(exec_name)
        self.run_with_log_args(exec_name)
        self.run_with_top_args(exec_name)
        self.run_with_stats_args(exec_name)
        self.get_cmd_return(exec_name, '--total')
        self.get_cmd_return(exec_name, '--per-tid')
        self.get_cmd_return(exec_name, '--per-prio')

    def test_all_options_schedtop(self):
        exec_name = 'lttng-schedtop'
        self.run_all_options_sched(exec_name)

    def test_all_options_schedfreq(self):
        exec_name = 'lttng-schedfreq'
        self.run_all_options_sched(exec_name)
        self.get_cmd_return(exec_name, '--per-prio --freq-uniform')
        self.get_cmd_return(exec_name, '--per-tid --freq-uniform')
        self.get_cmd_return(exec_name, '--total --freq-uniform')

    def test_all_options_schedlog(self):
        exec_name = 'lttng-schedlog'
        self.run_all_options_sched(exec_name)

    def test_all_options_schedstats(self):
        exec_name = 'lttng-schedstats'
        self.run_all_options_sched(exec_name)

    # lttng-syscallstats
    def test_all_options_syscallstats(self):
        exec_name = 'lttng-syscallstats'
        self.run_with_common_options(exec_name)
        self.run_with_proc_filter_args(exec_name)
