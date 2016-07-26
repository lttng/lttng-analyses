# The MIT License (MIT)
#
# Copyright (C) 2016 - Philippe Proulx <pproulx@efficios.com>
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

import babeltrace as bt
import collections


_CTF_SCOPES = (
    bt.CTFScope.EVENT_FIELDS,
    bt.CTFScope.EVENT_CONTEXT,
    bt.CTFScope.STREAM_EVENT_CONTEXT,
    bt.CTFScope.STREAM_EVENT_HEADER,
    bt.CTFScope.STREAM_PACKET_CONTEXT,
    bt.CTFScope.TRACE_PACKET_HEADER,
)


# This class has an interface which is compatible with the
# babeltrace.reader.Event class. This is the result of a deep copy
# performed by LTTng analyses.
class Event(collections.Mapping):
    def __init__(self, bt_ev):
        self._copy_bt_event(bt_ev)

    def _copy_bt_event(self, bt_ev):
        self._name = bt_ev.name
        self._cycles = bt_ev.cycles
        self._timestamp = bt_ev.timestamp
        self._fields = {}

        for scope in _CTF_SCOPES:
            self._fields[scope] = {}

            for field_name in bt_ev.field_list_with_scope(scope):
                field_value = bt_ev.field_with_scope(field_name, scope)
                self._fields[scope][field_name] = field_value

    @property
    def name(self):
        return self._name

    @property
    def cycles(self):
        return self._cycles

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def handle(self):
        raise NotImplementedError()

    @property
    def trace_collection(self):
        raise NotImplementedError()

    def _get_first_field(self, field_name):
        for scope_fields in self._fields.values():
            if field_name in scope_fields:
                return scope_fields[field_name]

    def field_with_scope(self, field_name, scope):
        if scope not in self._fields:
            raise ValueError('Invalid scope provided')

        if field_name in self._fields[scope]:
            return self._fields[scope][field_name]

    def field_list_with_scope(self, scope):
        if scope not in self._fields:
            raise ValueError('Invalid scope provided')

        return list(self._fields[scope].keys())

    def __getitem__(self, field_name):
        field = self._get_first_field(field_name)

        if field is None:
            raise KeyError(field_name)

        return field

    def __iter__(self):
        for key in self.keys():
            yield key

    def __len__(self):
        count = 0

        for scope_fields in self._fields.values():
            count += len(scope_fields)

        return count

    def __contains__(self, field_name):
        return self._get_first_field(field_name) is not None

    def keys(self):
        keys = []

        for scope_fields in self._fields.values():
            keys += list(scope_fields.keys())

        return keys

    def get(self, field_name, default=None):
        field = self._get_first_field(field_name)

        if field is None:
            return default

        return field

    def items(self):
        raise NotImplementedError()
