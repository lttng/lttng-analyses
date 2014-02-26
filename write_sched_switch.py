#!/usr/bin/env python3
# ctf_writer.py
#
# Babeltrace CTF Writer example script.
#
# Copyright 2013 EfficiOS Inc.
#
# Author: Jeremie Galarneau <jeremie.galarneau@efficios.com>
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

import sys
import tempfile
from babeltrace import *

trace_path = tempfile.mkdtemp()

print("Writing trace at {}".format(trace_path))
writer = CTFWriter.Writer(trace_path)

clock = CTFWriter.Clock("A_clock")
clock.description = "Simple clock"

writer.add_clock(clock)
writer.add_environment_field("Python_version", str(sys.version_info))

stream_class = CTFWriter.StreamClass("test_stream")
stream_class.clock = clock

char8_type = CTFWriter.IntegerFieldDeclaration(8)
char8_type.signed = True
char8_type.encoding = CTFStringEncoding.UTF8
char8_type.alignment = 8

int32_type = CTFWriter.IntegerFieldDeclaration(32)
int32_type.signed = True
int32_type.alignment = 8

int64_type = CTFWriter.IntegerFieldDeclaration(64)
int64_type.signed = True
int64_type.alignment = 8

array_type = CTFWriter.ArrayFieldDeclaration(char8_type, 16)

sched_switch = CTFWriter.EventClass("sched_switch")

sched_switch.add_field(array_type, "_prev_comm")
sched_switch.add_field(int32_type, "_prev_tid")
sched_switch.add_field(int32_type, "_prev_prio")
sched_switch.add_field(int64_type, "_prev_state")
sched_switch.add_field(array_type, "_next_comm")
sched_switch.add_field(int32_type, "_next_tid")
sched_switch.add_field(int32_type, "_next_prio")

stream_class.add_event_class(sched_switch)
stream = writer.create_stream(stream_class)

def set_char_array(event, string):
    if len(string) > 16:
        string = string[0:16]
    else:
        string = "%s" % (string + "\0" * (16 - len(string)))

    for i in range(len(string)):
        a = event.field(i)
        a.value = ord(string[i])

def set_int(event, value):
    event.value = value

event = CTFWriter.Event(sched_switch)
clock.time = 1000

set_char_array(event.payload("_prev_comm"), "lttng-consumerd")
set_int(event.payload("_prev_tid"), 30664)
set_int(event.payload("_prev_prio"), 20)
set_int(event.payload("_prev_state"), 1)
set_char_array(event.payload("_next_comm"), "swapper/3")
set_int(event.payload("_next_tid"), 0)
set_int(event.payload("_next_prio"), 20)

stream.append_event(event)

stream.flush()
