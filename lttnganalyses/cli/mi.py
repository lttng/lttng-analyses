# The MIT License (MIT)
#
# Copyright (C) 2015 - Philippe Proulx <pproulx@efficios.com>
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


class Tags:
    CPU = 'cpu'
    MEMORY = 'memory'
    INTERRUPT = 'interrupt'
    SCHED = 'sched'
    SYSCALL = 'syscall'
    IO = 'io'
    TOP = 'top'
    STATS = 'stats'
    FREQ = 'freq'
    LOG = 'log'


class ColumnDescription:
    def __init__(self, key, title, do_class, unit=None):
        self._key = key
        self._title = title
        self._do_class = do_class
        self._unit = unit

    @property
    def key(self):
        return self._key

    def to_native_object(self):
        obj = {
            'title': self._title,
            'class': self._do_class,
        }

        if self._unit:
            obj['unit'] = self._unit

        return obj


class TableClass:
    def __init__(self, name, title, column_descriptions_tuples=None,
                 inherit=None):
        if column_descriptions_tuples is None:
            column_descriptions_tuples = []

        self._inherit = inherit
        self._name = name
        self._title = title
        self._column_descriptions = []

        for column_descr_tuple in column_descriptions_tuples:
            key = column_descr_tuple[0]
            title = column_descr_tuple[1]
            do_type = column_descr_tuple[2]
            unit = None

            if len(column_descr_tuple) > 3:
                unit = column_descr_tuple[3]

            column_descr = ColumnDescription(key, title, do_type.CLASS, unit)
            self._column_descriptions.append(column_descr)

    @property
    def name(self):
        return self._name

    @property
    def title(self):
        return self._title

    def to_native_object(self):
        obj = {}
        column_descrs = self._column_descriptions
        native_column_descrs = [c.to_native_object() for c in column_descrs]

        if self._inherit is not None:
            obj['inherit'] = self._inherit

        if self._title is not None:
            obj['title'] = self._title

        if native_column_descrs:
            obj['column-descriptions'] = native_column_descrs

        return obj

    def get_column_named_tuple(self):
        keys = [cd.key for cd in self._column_descriptions]

        return namedtuple('Column', keys)


class ResultTable:
    def __init__(self, table_class, begin, end, subtitle=None):
        self._table_class = table_class
        self._column_named_tuple = table_class.get_column_named_tuple()
        self._subtitle = subtitle
        self._timerange = TimeRange(begin, end)
        self._rows = []

    @property
    def table_class(self):
        return self._table_class

    @property
    def timerange(self):
        return self._timerange

    @property
    def title(self):
        return self._table_class.title

    @property
    def subtitle(self):
        return self._subtitle

    def append_row(self, **kwargs):
        row = self._column_named_tuple(**kwargs)
        self._rows.append(row)

    def append_row_tuple(self, row_tuple):
        self._rows.append(row_tuple)

    @property
    def rows(self):
        return self._rows

    def to_native_object(self):
        obj = {
            'class': self._table_class.name,
            'time-range': self._timerange.to_native_object(),
        }
        row_objs = []

        if self._table_class.name:
            if self._subtitle is not None:
                full_title = '{} [{}]'.format(self.title, self._subtitle)
                table_class = TableClass(None, full_title,
                                         inherit=self._table_class.name)
                self._table_class = table_class

        if self._table_class.name is None:
            obj['class'] = self._table_class.to_native_object()

        for row in self._rows:
            row_obj = []

            for cell in row:
                row_obj.append(cell.to_native_object())

            row_objs.append(row_obj)

        obj['data'] = row_objs

        return obj


class _DataObject:
    def to_native_object(self):
        raise NotImplementedError

    def __eq__(self, other):
        # ensure we're comparing the same type first
        if not isinstance(other, self.__class__):
            return False

        # call specific equality method
        return self._eq(other)

    def _eq(self, other):
        raise NotImplementedError


class _UnstructuredDataObject(_DataObject):
    def __init__(self, value):
        self._value = value

    @property
    def value(self):
        return self._value

    def to_native_object(self):
        return self._value

    def __str__(self):
        return str(self._value)

    def _eq(self, other):
        return self._value == other._value


class _StructuredDataObject(_DataObject):
    def to_native_object(self):
        base = {'class': self.CLASS}
        base.update(self._to_native_object())

        return base

    def _to_native_object(self):
        raise NotImplementedError


class Boolean(_UnstructuredDataObject):
    CLASS = 'bool'


class Integer(_UnstructuredDataObject):
    CLASS = 'int'


class Float(_UnstructuredDataObject):
    CLASS = 'float'


class String(_UnstructuredDataObject):
    CLASS = 'string'


class Empty(_DataObject):
    def to_native_object(self):
        return None

    def _eq(self, other):
        return True


class Unknown(_StructuredDataObject):
    CLASS = 'unknown'

    def _to_native_object(self):
        return {}

    def _eq(self, other):
        return True

    def __str__(self):
        return '?'


class _SimpleValue(_StructuredDataObject):
    def __init__(self, value):
        self._value = value

    @property
    def value(self):
        return self._value

    def _to_native_object(self):
        return {'value': self._value}

    def __str__(self):
        return str(self._value)

    def _eq(self, other):
        return self._value == other._value


class _SimpleName(_StructuredDataObject):
    def __init__(self, name):
        self._name = name

    @property
    def name(self):
        return self._name

    def _to_native_object(self):
        return {'name': self._name}

    def __str__(self):
        return self._name

    def _eq(self, other):
        return self._name == other._name


class Ratio(_SimpleValue):
    CLASS = 'ratio'

    @classmethod
    def from_percentage(cls, value):
        return cls(value / 100)

    def to_percentage(self):
        return self._value * 100


class Timestamp(_SimpleValue):
    CLASS = 'timestamp'


class Duration(_SimpleValue):
    CLASS = 'duration'

    @classmethod
    def from_ms(cls, ms):
        return cls(ms * 1000000)

    @classmethod
    def from_us(cls, us):
        return cls(us * 1000)

    def to_ms(self):
        return self._value / 1000000

    def to_us(self):
        return self._value / 1000


class Size(_SimpleValue):
    CLASS = 'size'


class Bitrate(_SimpleValue):
    CLASS = 'bitrate'

    @classmethod
    def from_size_duration(cls, size, duration):
        return cls(size * 8 / duration)


class TimeRange(_StructuredDataObject):
    CLASS = 'time-range'

    def __init__(self, begin, end):
        self._begin = begin
        self._end = end

    @property
    def begin(self):
        return self._begin

    @property
    def end(self):
        return self._end

    def _to_native_object(self):
        return {'begin': self._begin, 'end': self._end}

    def _eq(self, other):
        return (self._begin, self._end) == (other._begin, other._end)


class Syscall(_SimpleName):
    CLASS = 'syscall'


class Process(_StructuredDataObject):
    CLASS = 'process'

    def __init__(self, name=None, pid=None, tid=None):
        self._name = name
        self._pid = pid
        self._tid = tid

    @property
    def name(self):
        return self._name

    @property
    def pid(self):
        return self._pid

    @property
    def tid(self):
        return self._tid

    def _to_native_object(self):
        ret_dict = {}

        if self._name is not None:
            ret_dict['name'] = self._name

        if self._pid is not None:
            ret_dict['pid'] = self._pid

        if self._tid is not None:
            ret_dict['tid'] = self._tid

        return ret_dict

    def _eq(self, other):
        self_tuple = (self._name, self._pid, self._tid)
        other_tuple = (other._name, other._pid, other._tid)

        return self_tuple == other_tuple


class Path(_StructuredDataObject):
    CLASS = 'path'

    def __init__(self, path):
        self._path = path

    @property
    def path(self):
        return self._path

    def _to_native_object(self):
        return {'path': self._path}

    def _eq(self, other):
        return self._path == other._path


class Fd(_StructuredDataObject):
    CLASS = 'fd'

    def __init__(self, fd):
        self._fd = fd

    @property
    def fd(self):
        return self._fd

    def _to_native_object(self):
        return {'fd': self._fd}

    def _eq(self, other):
        return self._fd == other._fd


class Irq(_StructuredDataObject):
    CLASS = 'irq'

    def __init__(self, is_hard, nr, name=None):
        self._is_hard = is_hard
        self._nr = nr
        self._name = name

    @property
    def is_hard(self):
        return self._is_hard

    @property
    def nr(self):
        return self._nr

    @property
    def name(self):
        return self._name

    def _to_native_object(self):
        obj = {'hard': self._is_hard, 'nr': self._nr}

        if self._name is not None:
            obj['name'] = self._name

        return obj

    def _eq(self, other):
        self_tuple = (self._is_hard, self._nr, self._name)
        other_tuple = (other._is_hard, other._nr, other._name)

        return self_tuple == other_tuple


class Cpu(_StructuredDataObject):
    CLASS = 'cpu'

    def __init__(self, cpu_id):
        self._id = cpu_id

    @property
    def id(self):
        return self._id

    def _to_native_object(self):
        return {'id': self._id}

    def _eq(self, other):
        return self._id == other._id


class Disk(_SimpleName):
    CLASS = 'disk'


class Partition(_SimpleName):
    CLASS = 'part'


class NetIf(_SimpleName):
    CLASS = 'netif'


def get_metadata(version, title, description, authors, url, tags,
                 table_classes):
    t_classes = {t.name: t.to_native_object() for t in table_classes}

    return {
        'version': {
            'major': version.major,
            'minor': version.minor,
            'patch': version.patch,
            'extra': version.extra
        },
        'title': title,
        'description': description,
        'authors': authors,
        'url': url,
        'tags': tags,
        'table-classes': t_classes,
    }
