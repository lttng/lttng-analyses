# The MIT License (MIT)
#
# Copyright (C) 2015 - Julien Desfossez <jdesfossez@efficios.com>
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
import sys
import time
from . import mi
from collections import namedtuple
from ..common import format_utils


try:
    from progressbar import ETA, Bar, Percentage, ProgressBar
    progressbar_available = True
except ImportError:
    progressbar_available = False


# approximation for the progress bar
_BYTES_PER_EVENT = 30


def get_folder_size(folder):
    total_size = os.path.getsize(folder)
    for item in os.listdir(folder):
        itempath = os.path.join(folder, item)
        if os.path.isfile(itempath):
            total_size += os.path.getsize(itempath)
        elif os.path.isdir(itempath):
            total_size += get_folder_size(itempath)
    return total_size


class _Progress:
    def __init__(self, ts_begin, ts_end, path, use_size=False):
        if ts_begin is None or ts_end is None or use_size:
            size = get_folder_size(path)
            self._maxval = size / _BYTES_PER_EVENT
            self._use_time = False
        else:
            self._maxval = ts_end - ts_begin
            self._ts_begin = ts_begin
            self._ts_end = ts_end
            self._use_time = True

        self._at = 0
        self._event_count = 0
        self._last_event_count_check = 0
        self._last_time_check = time.time()

    def update(self, event):
        self._event_count += 1

        if self._use_time:
            self._at = event.timestamp - self._ts_begin
        else:
            self._at = self._event_count

        if self._at > self._maxval:
            self._at = self._maxval

        if self._event_count - self._last_event_count_check >= 101:
            self._last_event_count_check = self._event_count
            now = time.time()

            if now - self._last_time_check >= .1:
                self._update_progress()
                self._last_time_check = now

    def _update_progress(self):
        pass

    def finalize(self):
        pass


class FancyProgressBar(_Progress):
    def __init__(self, ts_begin, ts_end, path, use_size):
        super().__init__(ts_begin, ts_end, path, use_size)
        self._pbar = None

        if progressbar_available:
            widgets = ['Processing the trace: ', Percentage(), ' ',
                       Bar(marker='#', left='[', right=']'),
                       ' ', ETA(), ' ']  # see docs for other options
            self._pbar = ProgressBar(widgets=widgets,
                                   maxval=self._maxval)
            self._pbar.start()
        else:
            print('Warning: progressbar module not available, '
                  'using --no-progress.', file=sys.stderr)

    def _update_progress(self):
        if self._pbar is None:
            return

        self._pbar.update(self._at)

    def finalize(self):
        if self._pbar is None:
            return

        self._pbar.finish()


class MiProgress(_Progress):
    def __init__(self, ts_begin, ts_end, path, use_size):
        super().__init__(ts_begin, ts_end, path, use_size)

        if self._use_time:
            fmt = 'Starting analysis from {} to {}'
            begin = format_utils.format_timestamp(self._ts_begin)
            end = format_utils.format_timestamp(self._ts_end)
            msg = fmt.format(begin, end)
        else:
            msg = 'Starting analysis: {} estimated events'.format(round(self._maxval))

        mi.print_progress(0, msg)

    def _update_progress(self):
        if self._at == self._maxval:
            mi.print_progress(1, 'Done!')
            return

        if self._use_time:
            ts_at = self._at + self._ts_begin
            at_ts = format_utils.format_timestamp(ts_at)
            end = format_utils.format_timestamp(self._ts_end)
            msg = '{}/{}; {} events processed'.format(at_ts, end, self._event_count)
        else:
            msg = '{} events processed'.format(self._event_count)

        mi.print_progress(round(self._at / self._maxval, 4), msg)

    def finalize(self):
        mi.print_progress(1, 'Done!')
