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
from progressbar import *
from LTTngAnalyzes.common import *

# These declarations will go in their own file
# They have been put here temporarily for testing
char8_type = CTFWriter.IntegerFieldDeclaration(8)
char8_type.signed = True
char8_type.encoding = CTFStringEncoding.UTF8
char8_type.alignment = 8

int8_type = CTFWriter.IntegerFieldDeclaration(8)
int8_type.signed = True
int8_type.alignment = 8

uint8_type = CTFWriter.IntegerFieldDeclaration(8)
uint8_type.signed = False
uint8_type.alignment = 8

int16_type = CTFWriter.IntegerFieldDeclaration(16)
int16_type.signed = True
int16_type.alignment = 8

uint16_type = CTFWriter.IntegerFieldDeclaration(16)
uint16_type.signed = False
uint16_type.alignment = 8

int32_type = CTFWriter.IntegerFieldDeclaration(32)
int32_type.signed = True
int32_type.alignment = 8

uint32_type = CTFWriter.IntegerFieldDeclaration(32)
uint32_type.signed = False
uint32_type.alignment = 8

int64_type = CTFWriter.IntegerFieldDeclaration(64)
int64_type.signed = True
int64_type.alignment = 8

uint64_type = CTFWriter.IntegerFieldDeclaration(64)
uint64_type.signed = False
uint64_type.alignment = 8

string_type = CTFWriter.StringFieldDeclaration()

class CTFFilter():
    def __init__(self, args, handle, traces):
        self.args = args
        self.handle = handle
        self.traces = traces

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
        elif field_type is StringFieldDeclaration:
            self.add_string_field(event_class, field)
        elif field_type is ArrayFieldDeclaration:
            self.add_array_field(event_class, field)
        elif field_type is SequenceFieldDeclaration:
            self.add_sequence_field(event_class, field)
        else:
            raise RuntimeError('Unsupported field type: '
                               + field_type.__name__)

    def add_int_field(self, event_class, field):
        # signed int
        if field.signedness == 1:
            if field.length == 8:
                event_class.add_field(int8_type, '_' + field.name)
            elif field.length == 16:
                event_class.add_field(int16_type, '_' + field.name)
            elif field.length == 32:
                event_class.add_field(int32_type, '_' + field.name)
            elif field.length == 64:
                event_class.add_field(int64_type, '_' + field.name)
            else:
                raise RuntimeError(
                    'Error, unsupported field length {0} bits of field {1}'
                    .format(field.length, field.name))
        # unsigned int
        elif field.signedness == 0:
            if field.length == 8:
                event_class.add_field(uint8_type, '_' + field.name)
            elif field.length == 16:
                event_class.add_field(uint16_type, '_' + field.name)
            elif field.length == 32:
                event_class.add_field(uint32_type, '_' + field.name)
            elif field.length == 64:
                event_class.add_field(uint64_type, '_' + field.name)
            else:
                raise RuntimeError(
                    'Error, unsupported field length {0} bits of field {1}'
                    .format(field.length, field.name))
        else:
            raise RuntimeError('Error, could not determine signedness of field'
                               + field.name)

    def add_string_field(self, event_class, field):
        string_type = CTFWriter.ArrayFieldDeclaration(char8_type, 16)
        event_class.add_field(string_type, '_' + field.name)

    def add_array_field(self, event_class, field):
        array_type = CTFWriter.ArrayFieldDeclaration(char8_type, field.length)
        event_class.add_field(array_type, '_' + field.name)

    def add_sequence_field(self, event_class, field):
        # stuff
        print('seq')

    def process_event(self, event):
        if event.name in ['lttng_statedump_start', 'lttng_statedump_end',
                          'sys_unknown', 'sys_geteuid', 'sys_getuid', 'sys_getegid']:
            return

        self.clock.time = event.timestamp
        writeable_event = CTFWriter.Event(self.event_classes[event.name])

        field_names = event.field_list_with_scope(CTFScope.EVENT_FIELDS)

        for field_name in field_names:
            self.set_field(writeable_event, field_name, event[field_name])

        try:
            self.stream.append_event(writeable_event)
        except ValueError:
            print(event.name)
            pass

    def set_field(self, writeable_event, field_name, value):
        field_type = type(value)

        if field_type is str:
            self.set_char_array(writeable_event.payload('_' + field_name), value)
        elif field_type is int:
            self.set_int(writeable_event.payload('_' + field_name), value)
        elif field_type is list:
            pass
        else:
            raise RuntimeError('Error, unsupported field type '
                               + field_type.__name__)

    def set_char_array(self, writeable_event, string):
        if len(string) > 16:
            string = string[0:16]
        else:
            string = "%s" % (string + "\0" * (16 - len(string)))

        for i in range(len(string)):
            a = writeable_event.field(i)
            a.value = ord(string[i])

    def set_int(self, writeable_event, value):
        writeable_event.value = value

    def run(self):
        size = getFolderSize(args.path)
        # size *= 2 # because we do 2 passes on the events
        widgets = ['Processing the trace: ', Percentage(), ' ',
                Bar(marker='#',left='[',right=']'), ' ', ETA(), ' ']

        if not args.no_progress:
            pbar = ProgressBar(widgets=widgets, maxval=size/BYTES_PER_EVENT)
            pbar.start()

        event_count = 0

        for event in self.handle.events:
            if not args.no_progress:
                try:
                    pbar.update(event_count)
                except ValueError:
                    pass

            self.process_event_metadata(event)
            event_count += 1

        self.stream = self.writer.create_stream(self.stream_class)

        for event in self.traces.events:
            if not args.no_progress:
                try:
                    pbar.update(event_count)
                except ValueError:
                    pass

            self.process_event(event)
            event_count += 1

        if not args.no_progress:
            pbar.finish()
            print

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
    parser.add_argument('--no-progress', action="store_true",
                        help='Don\'t display the progress bar')

    args = parser.parse_args()

    traces = TraceCollection()
    handle = traces.add_trace(args.path, 'ctf')
    if handle is None:
        sys.exit(1)

    ctf_filter = CTFFilter(args, handle, traces)

    ctf_filter.run()

    traces.remove_trace(handle)
