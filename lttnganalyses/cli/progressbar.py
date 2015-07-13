#!/usr/bin/env python3
#
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

try:
    from progressbar import ETA, Bar, Percentage, ProgressBar
    progressbar_available = True
except ImportError:
    progressbar_available = False

# approximation for the progress bar
BYTES_PER_EVENT = 30


def getFolderSize(folder):
    total_size = os.path.getsize(folder)
    for item in os.listdir(folder):
        itempath = os.path.join(folder, item)
        if os.path.isfile(itempath):
            total_size += os.path.getsize(itempath)
        elif os.path.isdir(itempath):
            total_size += getFolderSize(itempath)
    return total_size


def progressbar_setup(obj):
    if hasattr(obj, '_arg_no_progress') and obj._arg_no_progress:
        obj.pbar = None
        return

    if progressbar_available:
        size = getFolderSize(obj._arg_path)
        widgets = ['Processing the trace: ', Percentage(), ' ',
                   Bar(marker='#', left='[', right=']'),
                   ' ', ETA(), ' ']  # see docs for other options
        obj.pbar = ProgressBar(widgets=widgets,
                               maxval=size/BYTES_PER_EVENT)
        obj.pbar.start()
    else:
        print('Warning: progressbar module not available, '
              'using --no-progress.', file=sys.stderr)
        obj._arg_no_progress = True
        obj.pbar = None
    obj.event_count = 0


def progressbar_update(obj):
    if hasattr(obj, '_arg_no_progress') and \
            (obj._arg_no_progress or obj.pbar is None):
        return
    try:
        obj.pbar.update(obj.event_count)
    except ValueError:
        pass
    obj.event_count += 1


def progressbar_finish(obj):
    if hasattr(obj, '_arg_no_progress') and obj._arg_no_progress:
        return
    obj.pbar.finish()
