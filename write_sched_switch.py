#!/usr/bin/env python3

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

uint32_type = CTFWriter.IntegerFieldDeclaration(32)
uint32_type.signed = False
uint32_type.alignment = 8

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
sched_switch.add_field(uint32_type, "_cpu_id")

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

def write_sched_switch(time_ms, cpu_id, prev_comm, prev_tid, next_comm, \
        next_tid, prev_prio = 20, prev_state = 1, next_prio = 20):
    event = CTFWriter.Event(sched_switch)
    clock.time = time_ms * 1000000
    set_char_array(event.payload("_prev_comm"), prev_comm)
    set_int(event.payload("_prev_tid"), prev_tid)
    set_int(event.payload("_prev_prio"), prev_prio)
    set_int(event.payload("_prev_state"), prev_state)
    set_char_array(event.payload("_next_comm"), next_comm)
    set_int(event.payload("_next_tid"), next_tid)
    set_int(event.payload("_next_prio"), next_prio)
    set_int(event.payload("_cpu_id"), cpu_id)
    stream.append_event(event)
    stream.flush()

def sched_switch_50pc(start_time_ms, end_time_ms, cpu_id, period, \
        comm1, tid1, comm2, tid2):
    current = start_time_ms
    while current < end_time_ms:
        write_sched_switch(current, cpu_id, comm1, tid1, comm2, tid2)
        current += period
        write_sched_switch(current, cpu_id, comm2, tid2, comm1, tid1)
        current += period

sched_switch_50pc(1393345614000, 1393345615000, 0, 100, \
        "swapper/0", 0, "prog50pc-cpu0", 30664)
