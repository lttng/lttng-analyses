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

try:
    from . import _bt2 as bt

except ImportError:
    try:
        from . import _babeltrace as bt

    except ImportError:
        print("Error, no babeltrace implementation found.")

CTF_SCOPE_TRACE_PACKET_HEADER = bt.CTF_SCOPE_TRACE_PACKET_HEADER
CTF_SCOPE_STREAM_PACKET_CONTEXT = bt.CTF_SCOPE_STREAM_PACKET_CONTEXT
CTF_SCOPE_STREAM_EVENT_HEADER = bt.CTF_SCOPE_STREAM_EVENT_HEADER
CTF_SCOPE_STREAM_EVENT_CONTEXT = bt.CTF_SCOPE_STREAM_EVENT_CONTEXT
CTF_SCOPE_EVENT_CONTEXT = bt.CTF_SCOPE_EVENT_CONTEXT
CTF_SCOPE_EVENT_PAYLOAD = bt.CTF_SCOPE_EVENT_PAYLOAD
CTF_SCOPE_EVENT_FIELDS = bt.CTF_SCOPE_EVENT_FIELDS

CTF_VALUE_TYPE_UNKNOWN = bt.CTF_VALUE_TYPE_UNKNOWN
# CTF_VALUE_TYPE_NULL = bt.
# CTF_VALUE_TYPE_BOOL = bt.
CTF_VALUE_TYPE_INTEGER = bt.CTF_VALUE_TYPE_INTEGER
CTF_VALUE_TYPE_FLOAT = bt.CTF_VALUE_TYPE_FLOAT
CTF_VALUE_TYPE_STRING = bt.CTF_VALUE_TYPE_STRING
CTF_VALUE_TYPE_ARRAY = bt.CTF_VALUE_TYPE_ARRAY
# CTF_VALUE_TYPE_MAP = bt.C

CTF_STRING_ENCODING_UNKNOWN = bt.CTF_STRING_ENCODING_UNKNOWN
CTF_STRING_ENCODING_NONE = bt.CTF_STRING_ENCODING_NONE
CTF_STRING_ENCODING_UTF8 = bt.CTF_STRING_ENCODING_UTF8
CTF_STRING_ENCODING_ASCII = bt.CTF_STRING_ENCODING_ASCII


CTFWriter = bt.CTFWriter
TraceCollection = bt.TraceCollection

check_lost_events = bt.check_lost_events
get_tracer_version = bt.get_tracer_version
get_version = bt.get_version
has_intersect = bt.has_intersect
