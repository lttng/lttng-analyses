#!/usr/bin/env python3
#
# The MIT License (MIT)
#
# Copyright (c) 2014 Philippe Proulx <eepp.ca>
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
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


import sys
from setuptools import setup

# make sure we run Python 3+ here
v = sys.version_info
if v.major < 3:
    sys.stderr.write('Sorry, lttnganalysescli needs Python 3\n')
    sys.exit(1)

packages = [
    'lttnganalysescli',
    'ascii_graph',
]

install_requires = [
    'linuxautomaton',
    'lttnganalyses',
]

entry_points = {
    'console_scripts': [
        'lttng-cputop = lttnganalysescli.cputop:run',
        'lttng-iolatencyfreq = lttnganalysescli.io:runfreq',
        'lttng-iolatencystats = lttnganalysescli.io:runstats',
        'lttng-iolatencytop = lttnganalysescli.io:runlatencytop',
        'lttng-iolog = lttnganalysescli.io:runlog',
        'lttng-iousagetop = lttnganalysescli.io:runusage',
        'lttng-irqfreq = lttnganalysescli.irq:runfreq',
        'lttng-irqlog = lttnganalysescli.irq:runlog',
        'lttng-irqstats = lttnganalysescli.irq:runstats',
        'lttng-memtop = lttnganalysescli.memtop:run',
        'lttng-syscallstats = lttnganalysescli.syscallstats:run',
    ],
}

setup(name='lttnganalysescli',
      version='0.1.0',
      description='LTTng analyses CLI',
      author='Julien Desfossez',
      author_email='jdesfossez@efficios.com',
      packages=packages,
      install_requires=install_requires,
      entry_points=entry_points)
