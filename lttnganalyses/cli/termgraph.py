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

from collections import namedtuple


GraphDatum = namedtuple('GraphDatum', ['value', 'value_str', 'label'])


class BarGraph():
    MAX_BAR_WIDTH = 80
    BAR_CHAR = '█'
    HR_CHAR = '#'

    def __init__(self, data, get_value, get_label, get_value_str=None,
                 title=None, label_header=None, unit=None):
        self._max_value = 0
        self._max_value_len = 0
        self._title = title
        self._label_header = label_header
        self._unit = unit

        self._data = self._transform_data(
            data, get_value, get_value_str, get_label
        )

    def _transform_data(self, data, get_value, get_value_str, get_label):
        graph_data = []
        if get_value_str is None:
            get_value_str = self._get_value_str

        for datum in data:
            value = get_value(datum)
            value_str = get_value_str(value)
            value_len = len(value_str)
            label = get_label(datum)

            if value > self._max_value:
                self._max_value = value
            if value_len > self._max_value_len:
                self._max_value_len = value_len

            graph_data.append(GraphDatum(value, value_str, label))


        return graph_data

    def _get_graph_header(self):
        if not self._label_header:
            return self._title

        title_len = len(self._title)
        space_width = (self.MAX_BAR_WIDTH - title_len) + \
                      1 + self._max_value_len + 1

        return self._title + ' ' * space_width + self._label_header

    def _get_value_str(self, value):
        if isinstance(value, float):
            value_str = '{:0.02f}'.format(value)
        else:
            value_str = str(value)

        if self._unit:
            value_str += ' ' + self._unit

        return value_str

    def _get_bar_str(self, datum):
        bar_width = int(self.MAX_BAR_WIDTH * datum.value / self._max_value)
        space_width = self.MAX_BAR_WIDTH - bar_width
        bar_str = self.BAR_CHAR * bar_width + ' ' * space_width

        return bar_str

    def print_graph(self):
        if not self._data:
            return

        header = self._get_graph_header()

        print(header)
        print(self.HR_CHAR * self.MAX_BAR_WIDTH)
        for datum in self._data:
            bar_str = self._get_bar_str(datum)
            value_padding = ' ' * (self._max_value_len - len(datum.value_str))
            print(bar_str, value_padding + datum.value_str, datum.label)

        print()
