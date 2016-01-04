# The MIT License (MIT)
#
# Copyright (C) 2015 - Antoine Busque <abusque@efficios.com>
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

from functools import total_ordering


@total_ordering
class Version:
    def __init__(self, major, minor, patch, extra=None):
        self.major = major
        self.minor = minor
        self.patch = patch
        self.extra = extra

    def __lt__(self, other):
        if self.major < other.major:
            return True
        if self.major > other.major:
            return False

        if self.minor < other.minor:
            return True
        if self.minor > other.minor:
            return False

        return self.patch < other.patch

    def __eq__(self, other):
        return (
            self.major == other.major and
            self.minor == other.minor and
            self.patch == other.patch
        )

    def __repr__(self):
        version_str = '{}.{}.{}'.format(self.major, self.minor, self.patch)
        if self.extra:
            version_str += self.extra

        return version_str
