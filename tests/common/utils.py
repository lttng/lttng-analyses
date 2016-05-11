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

import os
import time

class TimezoneUtils():
    def __init__(self):
        self.original_tz = None

    def set_up_timezone(self):
        # Make sure that the local timezone as seen by the time module
        # is the same regardless of where the test is actually
        # run. US/Eastern was picked arbitrarily.
        self.original_tz = os.environ.get('TZ')
        os.environ['TZ'] = 'US/Eastern'
        try:
            time.tzset()
        except AttributeError:
            print('Warning: time.tzset() is unavailable on Windows.'
                  'This may cause test failures.')

    def tear_down_timezone(self):
        # Restore the original value of TZ if any, else delete it from
        # the environment variables.
        if self.original_tz:
            os.environ['TZ'] = self.original_tz
        else:
            del os.environ['TZ']
