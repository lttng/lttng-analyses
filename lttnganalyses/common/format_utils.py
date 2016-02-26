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

import math


def format_size(size, binary_prefix=True):
    """Convert an integral number of bytes to a human-readable string

    Args:
        size (int): a non-negative number of bytes
        binary_prefix (bool, optional): whether to use binary units
            prefixes, over SI prefixes. default: True

    Returns:
        The formatted string comprised of the size and units

    Raises:
        ValueError: if size < 0
    """
    if size < 0:
        raise ValueError('Cannot format negative size')

    if binary_prefix:
        base = 1024
        units = ['  B', 'KiB', 'MiB', 'GiB','TiB', 'PiB', 'EiB', 'ZiB', 'YiB']
    else:
        base = 1000
        units = [' B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']

    if size == 0:
        exponent = 0
    else:
        exponent = int(math.log(size, base))
        if exponent >= len(units):
            # Don't try and use a unit above YiB/YB
            exponent = len(units) - 1

        size /= math.pow(base, exponent)

    unit = units[exponent]

    if exponent == 0:
        # Don't display fractions of a byte
        format_str = '{:0.0f} {}'
    else:
        format_str = '{:0.2f} {}'

    return format_str.format(size, unit)

def format_prio_list(prio_list):
    """Format a list of prios into a string of unique prios with count

    Args:
        prio_list: a list of PrioEvent objects

    Returns:
        The formatted string containing the unique priorities and
        their count if they occurred more than once.
    """
    prio_count = {}
    prio_str = None

    for prio_event in prio_list:
        prio = prio_event.prio
        if prio not in prio_count:
            prio_count[prio] = 0

        prio_count[prio] += 1

    for prio in sorted(prio_count.keys()):
        count = prio_count[prio]
        if count > 1:
            count_str = ' ({} times)'.format(count)
        else:
            count_str = ''

        if prio_str is None:
            prio_str = '[{}{}'.format(prio, count_str)
        else:
            prio_str += ', {}{}'.format(prio, count_str)

    if prio_str is None:
        prio_str = '[]'
    else:
        prio_str += ']'

    return prio_str
