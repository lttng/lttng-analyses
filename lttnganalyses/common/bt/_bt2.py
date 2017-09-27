# The MIT License (MIT)
#
# Copyright (C) 2017 - Michael Jeanson <mjeanson@efficios.com>
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

import bt2

from ..version_utils import Version

CTF_SCOPE_UNKNOWN = bt2.native_bt.CTF_SCOPE_UNKNOWN
CTF_SCOPE_TRACE_PACKET_HEADER = bt2.native_bt.CTF_SCOPE_TRACE_PACKET_HEADER
CTF_SCOPE_STREAM_PACKET_CONTEXT = bt2.native_bt.CTF_SCOPE_STREAM_PACKET_CONTEXT
CTF_SCOPE_STREAM_EVENT_HEADER = bt2.native_bt.CTF_SCOPE_STREAM_EVENT_HEADER
CTF_SCOPE_STREAM_EVENT_CONTEXT = bt2.native_bt.CTF_SCOPE_STREAM_EVENT_CONTEXT
CTF_SCOPE_EVENT_CONTEXT = bt2.native_bt.CTF_SCOPE_EVENT_CONTEXT
CTF_SCOPE_EVENT_PAYLOAD = bt2.native_bt.CTF_SCOPE_EVENT_PAYLOAD
CTF_SCOPE_EVENT_FIELDS = bt2.native_bt.CTF_SCOPE_EVENT_FIELDS

CTF_VALUE_TYPE_UNKNOWN = bt2.native_bt.VALUE_TYPE_UNKNOWN
CTF_VALUE_TYPE_NULL = bt2.native_bt.VALUE_TYPE_NULL
CTF_VALUE_TYPE_BOOL = bt2.native_bt.VALUE_TYPE_BOOL
CTF_VALUE_TYPE_INTEGER = bt2.native_bt.VALUE_TYPE_INTEGER
CTF_VALUE_TYPE_FLOAT = bt2.native_bt.VALUE_TYPE_FLOAT
CTF_VALUE_TYPE_STRING = bt2.native_bt.VALUE_TYPE_STRING
CTF_VALUE_TYPE_ARRAY = bt2.native_bt.VALUE_TYPE_ARRAY
CTF_VALUE_TYPE_MAP = bt2.native_bt.VALUE_TYPE_MAP

CTF_STRING_ENCODING_UNKNOWN = bt2.native_bt.CTF_STRING_ENCODING_UNKNOWN
CTF_STRING_ENCODING_NONE = bt2.native_bt.CTF_STRING_ENCODING_NONE
CTF_STRING_ENCODING_UTF8 = bt2.native_bt.CTF_STRING_ENCODING_UTF8
CTF_STRING_ENCODING_ASCII = bt2.native_bt.CTF_STRING_ENCODING_ASCII


def get_version():
    return Version(bt2.native_bt.version_get_major(),
                   bt2.native_bt.version_get_minor(),
                   bt2.native_bt.version_get_patch())


def has_intersect():
    return True


def _get_trace_env(trace_path):
    notif_iter = bt2.TraceCollectionNotificationIterator([
        bt2.SourceComponentSpec('ctf', 'fs', trace_path)
    ])

    # raises if the trace contains no streams
    first_notif = next(notif_iter)
    assert(type(first_notif) is bt2.StreamBeginningNotification)

    return first_notif.stream.stream_class.trace.env


def get_tracer_version(trace_path):
    env = _get_trace_env(trace_path)

    if ('major_match' not in env or
            'minor_match' not in env or
            'patch_match' not in env):
        return False

    return Version(env['major_match'],
                   env['minor_match'],
                   env['patch_match'])


def check_lost_events(trace_path):
    # TODO
    return
