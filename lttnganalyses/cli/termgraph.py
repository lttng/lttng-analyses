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


GraphDatum = namedtuple('GraphDatum', ['value', 'value_str'])
BarGraphDatum = namedtuple('BarGraphDatum', ['value', 'value_str', 'label'])
FreqGraphDatum = namedtuple(
    'FreqGraphDatum', ['value', 'value_str', 'lower_bound']
)


class Graph():
    MAX_GRAPH_WIDTH = 80
    BAR_CHAR = '█'
    HR_CHAR = '#'

    def __init__(self, data, get_value, get_value_str, title, unit):
        self._data = data
        self._get_value = get_value
        self._title = title
        self._unit = unit
        self._max_value = 0
        self._max_value_len = 0

        if get_value_str is not None:
            self._get_value_str_cb = get_value_str
        else:
            self._get_value_str_cb = Graph._get_value_str_default

    def _transform_data(self, data):
        graph_data = []

        for datum in data:
            graph_datum = self._get_graph_datum(datum)

            if graph_datum.value > self._max_value:
                self._max_value = graph_datum.value
            if len(graph_datum.value_str) > self._max_value_len:
                self._max_value_len = len(graph_datum.value_str)

            graph_data.append(graph_datum)

        return graph_data

    def _get_value_str(self, value):
        return self._get_value_str_cb(value)

    def _get_graph_datum(self, datum):
        value = self._get_value(datum)
        value_str = self._get_value_str(value)

        return GraphDatum(value, value_str)

    def _print_header(self):
        if self._title:
            print(self._title)

    def _print_separator(self):
        print(self.HR_CHAR * self.MAX_GRAPH_WIDTH)

    def _print_body(self):
        raise NotImplementedError()

    def print_graph(self):
        if not self._data:
            return

        self._print_header()
        self._print_separator()
        self._print_body()
        print()

    @staticmethod
    def _get_value_str_default(value):
        if isinstance(value, float):
            value_str = '{:0.02f}'.format(value)
        else:
            value_str = str(value)

        return value_str


class BarGraph(Graph):
    def __init__(self, data, get_value, get_label, get_value_str=None,
                 title=None, label_header=None, unit=None):
        super().__init__(data, get_value, get_value_str, title, unit)

        self._get_label = get_label
        self._label_header = label_header
        self._data = self._transform_data(self._data)

    def _get_graph_datum(self, datum):
        value = self._get_value(datum)
        value_str = self._get_value_str(value)
        label = self._get_label(datum)

        return BarGraphDatum(value, value_str, label)

    def _get_value_str(self, value):
        value_str = super()._get_value_str(value)
        if self._unit:
            value_str += ' ' + self._unit

        return value_str

    def _get_graph_header(self):
        if not self._label_header:
            return self._title

        title_len = len(self._title)
        space_width = (
            self.MAX_GRAPH_WIDTH - title_len + 1 + self._max_value_len + 1
        )

        return self._title + ' ' * space_width + self._label_header

    def _print_header(self):
        header = self._get_graph_header()
        print(header)

    def _get_bar_str(self, datum):
        if self._max_value == 0:
            bar_width = 0
        else:
            bar_width = int(self.MAX_GRAPH_WIDTH * datum.value /
                            self._max_value)
        space_width = self.MAX_GRAPH_WIDTH - bar_width
        bar_str = self.BAR_CHAR * bar_width + ' ' * space_width

        return bar_str

    def _print_body(self):
        for datum in self._data:
            bar_str = self._get_bar_str(datum)
            value_padding = ' ' * (self._max_value_len - len(datum.value_str))
            print(bar_str, value_padding + datum.value_str, datum.label)


class FreqGraph(Graph):
    LOWER_BOUND_WIDTH = 8

    def __init__(self, data, get_value, get_lower_bound,
                 get_value_str=None, title=None, unit=None):
        super().__init__(data, get_value, get_value_str, title, unit)

        self._get_lower_bound = get_lower_bound
        self._data = self._transform_data(self._data)

    def _get_graph_datum(self, datum):
        value = self._get_value(datum)
        value_str = self._get_value_str(value)
        lower_bound = self._get_lower_bound(datum)

        return FreqGraphDatum(value, value_str, lower_bound)

    def _print_header(self):
        header = self._title
        if self._unit:
            header += ' ({})'.format(self._unit)

        print(header)

    def _get_bar_str(self, datum):
        max_width = self.MAX_GRAPH_WIDTH - self.LOWER_BOUND_WIDTH
        if self._max_value == 0:
            bar_width = 0
        else:
            bar_width = int(max_width * datum.value / self._max_value)
        space_width = max_width - bar_width
        bar_str = self.BAR_CHAR * bar_width + ' ' * space_width

        return bar_str

    def _print_body(self):
        for datum in self._data:
            bound_str = FreqGraph._get_bound_str(datum)
            bar_str = self._get_bar_str(datum)
            value_padding = ' ' * (self._max_value_len - len(datum.value_str))
            print(bound_str, bar_str, value_padding + datum.value_str)

    @staticmethod
    def _get_bound_str(datum):
        return '{:>7.03f}'.format(datum.lower_bound)
