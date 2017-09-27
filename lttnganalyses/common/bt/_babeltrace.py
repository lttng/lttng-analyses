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

import babeltrace as bt
from babeltrace import TraceCollection, CTFWriter

from ..version_utils import Version
import subprocess
import sys
import shlex
import os
import re

BT_INTERSECT_VERSION = Version(1, 4, 0)

CTF_SCOPE_TRACE_PACKET_HEADER = bt.CTFScope.TRACE_PACKET_HEADER
CTF_SCOPE_STREAM_PACKET_CONTEXT = bt.CTFScope.STREAM_PACKET_CONTEXT
CTF_SCOPE_STREAM_EVENT_HEADER = bt.CTFScope.STREAM_EVENT_HEADER
CTF_SCOPE_STREAM_EVENT_CONTEXT = bt.CTFScope.STREAM_EVENT_CONTEXT
CTF_SCOPE_EVENT_CONTEXT = bt.CTFScope.EVENT_CONTEXT
CTF_SCOPE_EVENT_PAYLOAD = bt.CTFScope.EVENT_FIELDS
CTF_SCOPE_EVENT_FIELDS = bt.CTFScope.EVENT_FIELDS

CTF_VALUE_TYPE_UNKNOWN = bt.CTFTypeId.UNKNOWN
# CTF_VALUE_TYPE_NULL = bt.CTFTypeId.NULL
# CTF_VALUE_TYPE_BOOL = bt.CTFTypeId.BOOL
CTF_VALUE_TYPE_INTEGER = bt.CTFTypeId.INTEGER
CTF_VALUE_TYPE_FLOAT = bt.CTFTypeId.FLOAT
CTF_VALUE_TYPE_STRING = bt.CTFTypeId.STRING
CTF_VALUE_TYPE_ARRAY = bt.CTFTypeId.ARRAY
# CTF_VALUE_TYPE_MAP = bt.CTFTypeId.MAP

CTF_STRING_ENCODING_UNKNOWN = bt.CTFStringEncoding.UNKNOWN
CTF_STRING_ENCODING_NONE = bt.CTFStringEncoding.NONE
CTF_STRING_ENCODING_UTF8 = bt.CTFStringEncoding.UTF8
CTF_STRING_ENCODING_ASCII = bt.CTFStringEncoding.ASCII


def get_version():
    try:
        output = subprocess.check_output('babeltrace')
    except subprocess.CalledProcessError:
        raise ValueError('Could not run babeltrace to verify version')

    output = output.decode(sys.stdout.encoding)
    first_line = output.splitlines()[0]
    version_string = first_line.split()[-1]

    return Version.new_from_string(version_string)


def has_intersect():
    return get_version() >= BT_INTERSECT_VERSION


def get_tracer_version(trace_path):
    ret = 1
    metadata = None

    try:
        ret, metadata = subprocess.getstatusoutput(
            'babeltrace -o ctf-metadata {}'.format(
                shlex.quote(trace_path)))
    except subprocess.CalledProcessError:
        pass

    # fallback to reading the text metadata if babeltrace failed to
    # output the CTF metadata
    if ret != 0:
        try:
            metadata_f = open(os.path.join(trace_path, 'metadata'), 'r')
            metadata = metadata_f.read()
            metadata_f.close()
        except OSError:
            raise ValueError('Cannot read the metadata of the trace, cannot'
                             'extract tracer version')

    major_match = re.search(r'tracer_major = "*(\d+)"*', metadata)
    minor_match = re.search(r'tracer_minor = "*(\d+)"*', metadata)
    patch_match = re.search(r'tracer_patchlevel = "*(\d+)"*', metadata)

    if not major_match or not minor_match or not patch_match:
            raise ValueError('Malformed metadata, cannot read tracer version')

    return Version(int(major_match.group(1)),
                   int(minor_match.group(1)),
                   int(patch_match.group(1)))


def check_lost_events(trace_path):
    try:
        subprocess.check_output('babeltrace {}'.format(
                                shlex.quote(trace_path)),
                                shell=True)
    except subprocess.CalledProcessError:
        raise ValueError('Cannot run babeltrace on the trace, cannot verify'
                         ' if events were lost during the trace recording')
