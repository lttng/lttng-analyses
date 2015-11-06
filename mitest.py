#!/usr/bin/python3

import json
import string
import random
import argparse
from lttnganalyses.cli import mi


_TABLE_CLASS_PER_PROC = 'per-proc'
_TABLE_CLASS_PER_SYSCALL = 'per-syscall'
_TABLE_CLASS_PER_IRQ = 'per-irq'
_TABLE_CLASSES = {
    _TABLE_CLASS_PER_PROC: mi.TableClass(
        _TABLE_CLASS_PER_PROC,
        'Per-process stuff', [
            ('proc', 'Process', mi.Process),
            ('count', 'Count', mi.Integer, 'things'),
            ('flag', 'Flag', mi.Boolean),
            ('value', 'Value', mi.Float, 'thou'),
            ('name', 'Name', mi.String),
            ('ratio', 'Ratio', mi.Ratio),
            ('ts', 'Timestamp', mi.Timestamp),
        ]
    ),
    _TABLE_CLASS_PER_SYSCALL: mi.TableClass(
        _TABLE_CLASS_PER_SYSCALL,
        'Per-syscall stuff', [
            ('syscall', 'System call', mi.Syscall),
            ('duration', 'Duration', mi.Duration),
            ('size', 'Size', mi.Size),
            ('bitrate', 'Bitrate', mi.Bitrate),
            ('time_range', 'Time range', mi.TimeRange),
        ]
    ),
    _TABLE_CLASS_PER_IRQ: mi.TableClass(
        _TABLE_CLASS_PER_IRQ,
        'Per-interrupt stuff', [
            ('interrupt', 'Interrupt', mi.Irq),
            ('fd', 'File descriptor', mi.Fd),
            ('path', 'File path', mi.Path),
            ('cpu', 'CPU', mi.Cpu),
            ('disk', 'Disk', mi.Disk),
            ('part', 'Partition', mi.Partition),
            ('netif', 'Network interface', mi.NetIf),
        ]
    )
}


def _print_metadata():
    infos = mi.get_metadata(version=[1, 2, 3, 'dev'], title='LAMI test',
                            description='LTTng analyses machine interface test',
                            authors=['Phil Proulx'], url='http://perdu.com',
                            tags=['lami', 'test'],
                            table_classes=_TABLE_CLASSES.values())
    print(json.dumps(infos))


def _parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--metadata', action='store_true')
    ap.add_argument('--begin', type=int, default=1000)
    ap.add_argument('--end', type=int, default=2000)
    ap.add_argument('-d', '--dynamic', action='store_true')
    ap.add_argument('-r', '--dynamic-rows', type=int, default=25)
    ap.add_argument('-c', '--dynamic-columns', type=int, default=10)

    return ap.parse_args()


def _print_tables(tables):
    obj = {
        'results': [t.to_native_object() for t in tables],
    }

    print(json.dumps(obj))


def _print_dynamic_table(begin, end, rows, columns):
    def gen_irq_name(size=6, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))

    column_tuples = [
        ('irq', 'Interrupt', mi.Irq),
    ]

    for i in range(columns):
        column_tuples.append((
            'count{}'.format(i),
            'Count ({} to {})'.format(i * 5, (i + 1) * 5),
            mi.Integer,
            'interrupts'
        ))

    table_class = mi.TableClass(None, 'What a dynamic table!', column_tuples)
    result_table = mi.ResultTable(table_class, begin, end)

    for i in range(rows):
        row_tuple = [
            mi.Irq(bool(random.getrandbits(1)), i, gen_irq_name())
        ]

        for j in range(columns):
            row_tuple.append(mi.Integer(random.randint(0, 5000)))

        result_table.append_row_tuple(tuple(row_tuple))

    _print_tables([result_table])


def _print_static_tables(begin, end):
    per_proc_table = mi.ResultTable(_TABLE_CLASSES[_TABLE_CLASS_PER_PROC], begin, end)
    per_syscall_table = mi.ResultTable(_TABLE_CLASSES[_TABLE_CLASS_PER_SYSCALL], begin, end)
    per_irq_table = mi.ResultTable(_TABLE_CLASSES[_TABLE_CLASS_PER_IRQ], begin, end)
    per_irq_table_sub = mi.ResultTable(_TABLE_CLASSES[_TABLE_CLASS_PER_IRQ], begin, end,
                                       'with overridden title')

    # per-process
    per_proc_table.append_row_tuple((
        mi.Process('zsh', pid=23),
        mi.Integer(23),
        mi.Boolean(False),
        mi.Float(17.2832),
        mi.String('typical'),
        mi.Ratio(0.154),
        mi.Timestamp(817232),
    ))
    per_proc_table.append_row_tuple((
        mi.Process('chromium', tid=4987),
        mi.Integer(19),
        mi.Boolean(False),
        mi.Float(-19457.15),
        mi.String('beam'),
        mi.Ratio(0.001),
        mi.Timestamp(1194875),
    ))
    per_proc_table.append_row_tuple((
        mi.Process('terminator'),
        mi.Integer(-145),
        mi.Unknown(),
        mi.Float(22.22),
        mi.String('dry'),
        mi.Ratio(0.94),
        mi.Timestamp(984987658),
    ))
    per_proc_table.append_row_tuple((
        mi.Process(pid=1945, tid=4497),
        mi.Integer(31416),
        mi.Boolean(True),
        mi.Float(17.34),
        mi.Empty(),
        mi.Ratio(1.5),
        mi.Timestamp(154484512),
    ))

    # per-syscall
    per_syscall_table.append_row_tuple((
        mi.Syscall('read'),
        mi.Duration(2398123),
        mi.Size(8123982),
        mi.Bitrate(223232),
        mi.TimeRange(98233, 1293828),
    ))
    per_syscall_table.append_row_tuple((
        mi.Syscall('write'),
        mi.Duration(412434),
        mi.Size(5645),
        mi.Bitrate(25235343),
        mi.TimeRange(5454, 2354523),
    ))
    per_syscall_table.append_row_tuple((
        mi.Syscall('sync'),
        mi.Duration(2312454),
        mi.Size(23433),
        mi.Empty(),
        mi.TimeRange(12, 645634545454),
    ))
    per_syscall_table.append_row_tuple((
        mi.Syscall('fstat'),
        mi.Unknown(),
        mi.Size(2343334),
        mi.Bitrate(5864684),
        mi.TimeRange(2134, 645634545),
    ))
    per_syscall_table.append_row_tuple((
        mi.Syscall('sync'),
        mi.Duration(564533),
        mi.Size(56875),
        mi.Bitrate(4494494494),
        mi.Empty(),
    ))

    # per-interrupt
    per_irq_table.append_row_tuple((
        mi.Irq(True, 15, 'keyboard'),
        mi.Fd(3),
        mi.Path('/etc/passwd'),
        mi.Cpu(2),
        mi.Disk('sda'),
        mi.Partition('sdb3'),
        mi.NetIf('eth0'),
    ))
    per_irq_table.append_row_tuple((
        mi.Irq(False, 7, 'soft-timer'),
        mi.Fd(1),
        mi.Path('/dev/null'),
        mi.Unknown(),
        mi.Disk('hda'),
        mi.Partition('mmcblk0p2'),
        mi.NetIf('enp3s25'),
    ))
    per_irq_table.append_row_tuple((
        mi.Irq(True, 34),
        mi.Empty(),
        mi.Empty(),
        mi.Cpu(1),
        mi.Disk('sdc'),
        mi.Partition('sdc3'),
        mi.NetIf('lo'),
    ))

    # per-interrupt with subtitle
    per_irq_table_sub.append_row_tuple((
        mi.Irq(False, 12, 'soft-like-silk'),
        mi.Fd(10),
        mi.Path('/home/bob/meowmix.txt'),
        mi.Cpu(0),
        mi.Disk('sdb'),
        mi.Partition('sdb2'),
        mi.NetIf('eth1'),
    ))
    per_irq_table_sub.append_row_tuple((
        mi.Irq(True, 1, 'mouse2'),
        mi.Fd(5),
        mi.Empty(),
        mi.Cpu(7),
        mi.Disk('vda'),
        mi.Partition('vda3'),
        mi.NetIf('wlp3s0'),
    ))

    # print
    _print_tables([
        per_proc_table,
        per_syscall_table,
        per_irq_table,
        per_irq_table_sub,
    ])


def _mitest():
    args = _parse_args()

    if args.metadata:
        _print_metadata()
        return

    if args.dynamic:
        _print_dynamic_table(args.begin, args.end,
                             args.dynamic_rows, args.dynamic_columns)
    else:
        _print_static_tables(args.begin, args.end)


if __name__ == '__main__':
    _mitest()
