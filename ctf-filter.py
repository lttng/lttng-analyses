#!/usr/bin/env python3
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the 'Software'), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

import argparse
from babeltrace import *

# These declarations will go in their own file
# They have been put here temporarily for testing
int32_type = CTFWriter.IntegerFieldDeclaration(32)
int32_type.signed = True
int32_type.alignment = 8

uint32_type = CTFWriter.IntegerFieldDeclaration(32)
uint32_type.signed = False
uint32_type.alignment = 8

int64_type = CTFWriter.IntegerFieldDeclaration(64)
int64_type.signed = True
int64_type.alignment = 8

int64_type = CTFWriter.IntegerFieldDeclaration(64)
int64_type.signed = False
int64_type.alignment = 8

class CTFFilter():
    def __init__(self, args, handle):
        self.args = args
        self.handle = handle

        self.clock = CTFWriter.Clock('monotonic')
        self.clock.description = 'Monotonic Clock'
        self.clock.freq = 1000000000

        self.writer = CTFWriter.Writer(self.args.output)
        self.writer.add_clock(self.clock)

        self.stream_class = CTFWriter.StreamClass('test_stream')
        self.stream_class.clock = self.clock

        self.event_classes = {}

    def process_event_metadata(self, event):
        if event.name not in self.event_classes.keys():
            event_class = CTFWriter.EventClass(event.name)
            for field in event.fields_scope(CTFScope.EVENT_FIELDS):
                self.add_field(event_class, field)

            self.event_classes[event.name] = event_class
            self.stream_class.add_event_class(event_class)

    def add_field(self, event_class, field):
        field_type = type(field)

        if field_type is IntegerFieldDeclaration:
            self.add_int_field(event_class, field)

    def process_event(self, event):
        raise NotImplementedError('process_event not yet implemented')

    def add_int_field(self, event_class, field):
        # signed int
        if field.signedness == 1:
            if field.length == 32:
                event_class.add_field(int32_type, '_' + field.name)
            elif field.length == 64:
                event_class.add_field(int64_type, '_' + field.name)
                # unsigned int
        elif field.signedness == 0:
            if field.length == 32:
                event_class.add_field(int32_type, '_' + field.name)
            elif field.length == 64:
                event_class.add_field(int64_type, '_' + field.name)
        else:
            raise RuntimeError('Error, could not determine signedness of field'
                               + field.name)


    def run(self):
        for event in self.handle.events:
            self.process_event_metadata(event)

        self.stream = self.writer.create_stream(self.stream_class)

        for event in self.handle.events:
            self.process_event(event)

        self.stream.flush()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('path', metavar='<path/to/trace>', help='Trace path')
    parser.add_argument('output', metavar='<path/to/new/trace>',
                        help='Location of file to which the resulting filtered\
                        trace will be written')
    parser.add_argument('-n', '--name', type=str, default='',
                        help='Name of events to keep\
                        (or discard when --discard is used)')
    parser.add_argument('--discard', action='store_true',
                        help='Discard specifed events instead of keeping them')

    args = parser.parse_args()

    traces = TraceCollection()
    handle = traces.add_trace(args.path, 'ctf')
    if handle is None:
        sys.exit(1)

    ctf_filter = CTFFilter(args, handle)

    ctf_filter.run()

    traces.remove_trace(handle)
