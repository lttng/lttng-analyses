# LTTng analyses machine interface (LAMI) v0.1

This document explains the input and output formats of the LTTng
analyses' **machine interface** (LAMI), version 0.1.

The LTTng analyses project is a set of scripts which analyze one or more
traces and output the results of this analysis. Each script is
responsible for one analysis.


## Definitions

  * **Analysis**: A producer of LAMI. An analysis is a program which
    receives an input following the LAMI [input format](#input-format),
    performs an analysis on a set of traces, and outputs the results
    following the LAMI [output format](#output-format).
  * **Consumer**: A consumer of LAMI. A consumer, usually some sort of
    user interface, executes an analysis program following the LAMI
    input format, and receives its results, following the LAMI output
    format.


## Input format

A consumer executes an analysis program with one or more standard
command-line arguments, then reads the standard output of the analysis
to its metadata or results following the [output
format](#output-format).

There are two different phases of analysis execution:

  1. **Metadata phase**: The consumer obtains the static metadata of
     the analysis.
  2. **Analysis phase**: The consumer can perform as many analyses as
     needed on different time ranges and set of traces, using the
     metadata of step 1 to interpret the results.

Having two phases avoids attaching the same metadata to each result
of a given analysis.

The LAMI input format is a list of standard command-line arguments.

**Metadata phase**:

| Argument | Description | Required? | Default |
|---|---|---|---|
| `--metadata` | Output the analysis' metadata instead of analyzing | Yes | N/A |

**Analysis phase**:

| Argument | Description | Required? | Default |
|---|---|---|---|
| 1st positional | Path to trace(s) to analyze | Yes | N/A |
| `--begin=TS` | Set beginning timestamp of analysis to `TS` ns | No | Absolute beginning of the analyzed traces |
| `--end=TS` | Set end timestamp of analysis to `TS` ns | No | Absolute end of the analyzed traces |
| `--limit=COUNT` | Set maximum number of output rows per result table to `COUNT` (use `unlimited` for no maximum number of rows) | No | `unlimited` |
| `--output-progress` | Output [progress data](#progress) before outputting the results | No | No progress output |


## Output format

The LAMI output format is produced by the analysis and is consumed by
the consumer.

An analysis has two output channels:

  1. Its standard output, which contains progress data, a metadata
     object, an analysis result object, or an error object.
  2. Its exit status, which indicates if the analysis was successful
     or not.

If an analysis is successful, its exit status is set to 0. Otherwise,
it's set to non-zero.

During the [metadata phase](#metadata), the standard output of the
analysis provides everything about the analysis which is not result
data: analysis title, authors, description, result table column
classes/titles/units, etc. This metadata is essential to interpret the
result objects of the analysis phase.

The output format of the metadata phase is always an
UTF-8 [JSON](http://json.org/) object.

During the [analysis phase](#analysis-phase), the consumer can perform
as many analyses as required by running the analysis with the mandatory
trace path argument.

The output format of the analysis phase depends on the command-line
arguments passed to the analysis program:

  * If `--output-progress` is passed, then the output format _may_
    contain [progress indication](#progress) lines, followed by an UTF-8
    [JSON](http://json.org/) object.
  * If `--output-progress` is _not_ passed, then the output format is
    always an UTF-8 [JSON](http://json.org/) object.

In all the objects of the output format, an unknown key must be
**ignored** by the consumer.


### Common objects

The following subsections document objects that can be written during
both the [metadata phase](#metadata) and the [analysis
phase](#analysis).


#### Error object

An _error object_ indicates that the analysis encountered an error
during its execution.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `error-code` | String or number | Error code | No | No error code |
| `error-message` | String | Error message | Yes | N/A |


**Example**:

```json
{
  "error-message": "Cannot open trace \"/root/lttng-traces/my-session\": Permission denied",
  "error-code": 1
}
```


#### Data objects

_Data objects_ contain result data of specific classes.

All data objects share a common `class` property which identifies the
object's class. The available values are:

| Class name (string) | Object |
|---|---|
| `unknown` | [Unknown object](#unknown-object) |
| `ratio` | [Ratio object](#ratio-object) |
| `timestamp` | [Timestamp object](#timestamp-object) |
| `time-range` | [Time range object](#time-range-object) |
| `duration` | [Duration object](#duration-object) |
| `size` | [Size object](#size-object) |
| `bitrate` | [Bitrate object](#bitrate-object) |
| `syscall` | [Syscall object](#syscall-object) |
| `process` | [Process object](#process-object) |
| `path` | [Path object](#path-object) |
| `fd` | [File descriptor object](#file-descriptor-object) |
| `irq` | [IRQ object](#irq-object) |
| `cpu` | [CPU object](#cpu-object) |
| `disk` | [Disk object](#disk-object) |
| `part` | [Disk partition object](#disk-partition-object) |
| `netif` | [Network interface object](#network-interface-object) |

The following subsections explain each class of data object.


##### Unknown object

The special _unknown object_ represents an unknown value. It is
typically used in result table cells where a given computation cannot
produce a result for some reason.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `class` | String | Set to `unknown` | Yes | N/A |

**Example**:

```json
{
  "class": "unknown"
}
```


##### Ratio object

A _ratio object_ describes a simple, dimensionless ratio, that is,
a relationship between two quantities having the same unit indicating
how many times the first quantity contains the second.

It is suggested that the consumer shows a ratio object as a percentage.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `class` | String | Set to `ratio` | Yes | N/A |
| `value` | Number | Ratio as a decimal fraction | Yes | N/A |

**Example**:

```json
{
  "class": "ratio",
  "value": 0.57
}
```


##### Timestamp object

A _timestamp object_ describes a specific point in time.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `class` | String | Set to `timestamp` | Yes | N/A |
| `value` | Number | Number of nanoseconds since Unix epoch | Yes | N/A |

**Example**:

```json
{
  "class": "timestamp",
  "value": 1444334398154194201
}
```


##### Time range object

A _time range object_ describes an interval bounded by two point in
time.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `class` | String | Set to `time-range` | Yes | N/A |
| `begin` | Number | Beginning timestamp (number of nanoseconds since Unix epoch) | Yes | N/A |
| `end` | Number | End timestamp (number of nanoseconds since Unix epoch) | Yes | N/A |

The `end` property must have a value greater or equal to the value of
the `begin` property.

**Examples**:

```json
{
  "class": "time-range",
  "begin": 1444334398154194201,
  "end": 1444334425194487548
}
```


##### Duration object

A _duration object_ describes the difference between two points in time.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `class` | String | Set to `duration` | Yes | N/A |
| `value` | Number | Time duration in nanoseconds | Yes | N/A |

**Example**:

```json
{
  "class": "duration",
  "value": 917238723
}
```


##### Size object

A _size object_ describes the size of a file, of a buffer, of a
transfer, etc.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `class` | String | Set to `size` | Yes | N/A |
| `value` | Integer | Size in bytes | Yes | N/A |

**Example**:

```json
{
  "class": "size",
  "value": 4994857
}
```


##### Bitrate object

A _bitrate object_ describes a transfer rate.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `class` | String | Set to `bitrate` | Yes | N/A |
| `value` | Number | Bitrate in bits/second | Yes | N/A |

**Example**:

```json
{
  "class": "bitrate",
  "value": 9845154
}
```


##### Syscall object

A _syscall object_ describes the name of a system call.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `class` | String | Set to `syscall` | Yes | N/A |
| `name` | String | System call name | Yes | N/A |

**Example**:

```json
{
  "class": "syscall",
  "name": "write"
}
```


##### Process object

A _process object_ describes a system process.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `class` | String | Set to `process` | Yes | N/A |
| `name` | String | Process name | No | No process name |
| `pid` | Integer | Process ID (PID) | No | No process ID |
| `tid` | Integer | Thread ID (TID) | No | No thread ID |

**Example**:

```json
{
  "class": "process",
  "name": "python",
  "pid": 1548,
  "tid": 1549
}
```


##### Path object

A _path object_ describes a relative or absolute file system path.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `class` | String | Set to `path` | Yes | N/A |
| `path` | String | File system path | Yes | N/A |

**Example**:

```json
{
  "class": "path",
  "path": "/usr/bin/grep"
}
```


##### File descriptor object

A _file descriptor object_ describes the numeric descriptor of a file.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `class` | String | Set to `fd` | Yes | N/A |
| `fd` | Integer | File descriptor | Yes | N/A |

**Example**:

```json
{
  "class": "fd",
  "fd": 8
}
```


##### IRQ object

An _IRQ object_ describes an interrupt source.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `class` | String | Set to `irq` | Yes | N/A |
| `hard` | Boolean | `true` if this interrupt source generates hardware interrupts, `false` for software interrupts | No | `true` |
| `nr` | Integer | Interrupt source number | Yes | N/A |
| `name` | String | Interrupt source name | No | No interrupt source name |

**Example**:

```json
{
  "class": "irq",
  "hard": true,
  "nr": 42,
  "name": "ahci"
}
```


##### CPU object

A _CPU object_ describes a numeric CPU identifier.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `class` | String | Set to `cpu` | Yes | N/A |
| `id` | Integer | CPU identifier number | Yes | N/A |

**Example**:

```json
{
  "class": "cpu",
  "id": 1
}
```


##### Disk object

A _disk object_ describes a disk name.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `class` | String | Set to `disk` | Yes | N/A |
| `name` | String | Disk name | Yes | N/A |

**Example**:

```json
{
  "class": "disk",
  "name": "sda"
}
```


##### Disk partition object

A _disk partition object_ describes a disk partition name.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `class` | String | Set to `part` | Yes | N/A |
| `name` | String | Disk partition name | Yes | N/A |

**Example**:

```json
{
  "class": "part",
  "name": "sdb2"
}
```


##### Network interface object

A _network interface object_ describes a network interface name.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `class` | String | Set to `netif` | Yes | N/A |
| `name` | String | Network interface name | Yes | N/A |

**Example**:

```json
{
  "class": "netif",
  "name": "eth0"
}
```


### Metadata

The _metadata phase_ explains the analysis. It provides an optional
title for the analysis and the format of the result tables (outputted
during the [analysis phase](#analysis) by the same analysis).

The metadata phase writes either:

  * A [metadata object](#metadata-object), or
  * An [error object](#error-object).

The following subsections document objects that can only be written
during the metadata phase.


#### Column description object

A _column description object_ describes one table _column_.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `title` | String | Column's title | No | No title |
| `class` | String | Class of data in column's cells, amongst: <ul><li>`string`: JSON strings</li><li>`int`: JSON numbers limited to integers</li><li>`number`: JSON numbers</li><li>`bool`: JSON booleans</li><li>`ratio`: [ratio objects](#ratio-object)</li><li>`timestamp`: [timestamp objects](#timestamp-object)</li><li>`time-range`: [time range objects](#time-range-object)</li><li>`duration`: [duration objects](#duration-object)</li><li>`size`: [size objects](#size-object)</li><li>`bitrate`: [bitrate objects](#bitrate-object)</li><li>`syscall`: [syscall objects](#syscall-object)</li><li>`process`: [process objects](#process-object)</li><li>`path`: [path objects](#path-object)</li><li>`fd`: [file descriptor objects](#file-descriptor-object)</li><li>`irq`: [IRQ objects](#irq-object)</li><li>`cpu`: [CPU objects](#cpu-object)</li><li>`disk`: [disk objects](#disk-object)</li><li>`part`: [disk partition objects](#disk-partition-object)</li><li>`netif`: [network interface objects](#network-interface-object)</li><li>`mixed`: any object</li></ul> | No | `mixed` |
| `unit` | String | Column's unit, if the `class` property is `string`, `int`, `number`, or `bool` | No | No unit |

**Examples**:

```json
{
  "title": "System call",
  "class": "syscall"
}
```

```json
{
  "title": "Count",
  "class": "int",
  "unit": "interrupts"
}
```


#### Table class object

A _table class object_ describes one class of
[result table](#result-table-object).

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `inherit` | String | Name of inherited table class | No | No inheritance |
| `title` | String | Table's title | No | No title |
| `column-descriptions` | Array of [column description objects](#column-description-object) | Descriptions of table's columns | No | Zero columns |

When inheriting another table class using the `inherit` property,
the `title` and `column-descriptions` properties override the
inherited values.

**Example** (no inheritance):

```json
{
  "title": "Handler duration and raise latency statistics (hard IRQ)",
  "column-descriptions": [
    {
      "title": "IRQ",
      "class": "irq"
    },
    {
      "title": "Count",
      "class": "int",
      "unit": "interrupts"
    },
    {
      "title": "Minimum duration",
      "class": "duration"
    },
    {
      "title": "Average duration",
      "class": "duration"
    },
    {
      "title": "Maximum duration",
      "class": "duration"
    },
    {
      "title": "Standard deviation",
      "class": "duration"
    }
  ]
}
```

**Example** (with inheritance, redefining the title, keeping the same
column descriptions):

```json
{
  "inherit": "irq-stats",
  "title": "IRQ statistics (ehci_hcd:usb1 [16])"
}
```


#### Version object

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `major` | Integer | Major version | Yes, if `minor` exists | No major version |
| `minor` | Integer | Minor version | Yes, if `patch` exists | No minor version |
| `patch` | Integer | Patch version | No | No patch version |
| `extra` | String | Extra version information (e.g., `dev`, `pre`, `rc2`, commit ID) | No | No extra version |

**Example**:

```json
{
  "major": 1,
  "minor": 2,
  "patch": 5,
  "extra": "dev"
}
```


#### Metadata object

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `mi-version` | [Version object](#version-object) | Latest version of the LAMI standard supported by this analysis, amongst:<ul><li>`{"major": 0, "minor": 1}`</li></ul> | Yes | N/A |
| `version` | [Version object](#version-object) | Version of the analysis | No | No version |
| `title` | String | Analysis title | No | No title |
| `authors` | Array of strings | Author(s) of the analysis | No | No authors |
| `description` | String | Analysis description | No | No description |
| `url` | String | URL where to find the analysis | No | No URL |
| `tags` | Array of strings | List of tags associated with the analysis | No | No tags |
| `table-classes` | Object mapping table class names (strings) to [table class objects](#table-class-object) | Classes of potential result tables | Yes (at least one table class) | N/A |

A consumer not implementing the LAMI standard version indicated by
the `mi-version` property should not perform the analysis.

The `table-classes` property describes all the potential result
tables with a static layout that can be generated by the
[analysis phase](#analysis). A result table can specify the name
of its table class, or define a full table class in place for
dynamic result tables.

**Example**:

```json
{
  "mi-version": {
    "major": 0,
    "minor": 1
  },
  "version": {
    "major": 1,
    "minor": 2,
    "patch": 5,
    "extra": "dev"
  },
  "title": "I/O latency statistics",
  "authors": [
    "Julien Desfossez",
    "Antoine Busque"
  ],
  "description": "Provides statistics about the latency involved in various I/O operations.",
  "url": "https://github.com/lttng/lttng-analyses",
  "tags": [
    "io",
    "stats",
    "linux-kernel",
    "lttng-analyses"
  ],
  "table-classes": {
    "syscall-latency": {
      "title": "System calls latency statistics",
      "column-descriptions": [
        {"title": "System call", "class": "syscall"},
        {"title": "Count", "class": "int", "unit": "operations"},
        {"title": "Minimum duration", "class": "duration"},
        {"title": "Average duration", "class": "duration"},
        {"title": "Maximum duration", "class": "duration"},
        {"title": "Standard deviation", "class": "duration"}
      ]
    },
    "disk-latency": {
      "title": "Disk latency statistics",
      "column-descriptions": [
        {"title": "Disk name", "class": "disk"},
        {"title": "Count", "class": "int", "unit": "operations"},
        {"title": "Minimum duration", "class": "duration"},
        {"title": "Average duration", "class": "duration"},
        {"title": "Maximum duration", "class": "duration"},
        {"title": "Standard deviation", "class": "duration"}
      ]
    }
  }
}
```


### Analysis

The _analysis phase_ outputs the actual data computer by the analysis.
The consumer needs the metadata object of the [metadata
phase](#metadata) in order to interpret the results of the analysis
phase.

If the `--output-progress` option is passed to the analysis program,
then the analysis _may_ output [progress indication](#progress) lines
before writing its main object.

Then, the analysis phase writes either:

  * A [result object](#analysis-results-object), or
  * An [error object](#error-object).

The following subsections document objects that can only be written
during the analysis phase.


#### Progress

Zero or more _progress lines_ may be written by the analysis during the
analysis phase _before_ it writes its main object. Progress lines are
only written if the `--output-progress` option is passed to the analysis
program.

The format of a progress line is as follows (plain text):

    VALUE[ MESSAGE]

where:

  * `VALUE`: a floating point number from 0 to 1 indicating the current
    progress of the analysis, or the string `*` which means that the
    analysis is not able to estimate when it will finish.
  * `MESSAGE`: an optional message which accompanies the progress
    indication.

Note that `VALUE` and `MESSAGE` are delimited by a single space
character.

The line must be terminated by a Unix newline (ASCII LF).

If one progress line has the `*` value, _all_ the progress lines should
have it.

**Example** (with progress value):

```
0 Starting the analysis
0 About to process 1248 events
0.17 38/1248 events procesed
0.342 142/1248 events processed
0.53 203/1248 events processed
0.54 Connecting to database
0.54 Connected
0.65
0.663
0.681 511/1248 events processed
0.759 810/1248 events processed
0.84 1051/1248 events processed
0.932 1194/1248 events processed
0.98 1248/1248 events processed
1 Done!
{ JSON result object }
```

**Example** (without progress value):

```
* Starting the analysis
* 124 events procesed
* 1150 events processed
* 3845 events processed
* Connecting to database
* Connected
* 9451 events processed
* 11542 events processed
* 15464 events processed
* 17704 events processed
* 21513 events processed
* Done!
{ JSON result object }
```


#### Result table object

A _result table object_ represents the data of an analysis in rows and
columns.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `time-range` | [Time range object](#time-range-object) | Time range over which the results contained in this table apply | Yes | N/A |
| `class` | String or [table class object](#table-class-object) | Table class name or table class object containing the metadata of this result table | Yes | N/A |
| `data` | Array of arrays of data objects/plain JSON values | Result table rows | Yes (at least one row) | N/A |

The `class` property indicates either:

  * The name of the [table class object](#table-class-object),
    as defined in the [metadata phase](#metadata), describing this
    result table.
  * A complete [table class object](#table-class-object). This is
    useful when the result table's layout is dynamic (dynamic title,
    dynamic column descriptions).

The `data` property is a JSON array of rows. Each row is a JSON array of
column cells. Each column cell contains a value (either a plain JSON
value, or a [data object](#data-objects)), as described by the `class`
property of the associated
[column description object](#column-description-object).

Any column cell may contain the [unknown object](#unknown-object) when
it would be possible to get a result for this cell, but the result is
unknown.

Any column cell may contain `null` when the cell is **empty**.

**Example**:

```json
{
  "time-range": {
    "class": "time-range",
    "begin": 1444334398154194201,
    "end": 1444334425194487548
  },
  "class": "syscall-latency",
  "data": [
    [
      {"class": "syscall", "name": "open"},
      45,
      {"class": "duration", "value": 5562},
      {"class": "duration", "value": 13835},
      {"class": "duration", "value": 77683},
      {"class": "duration", "value": 15263}
    ],
    [
      {"class": "syscall", "name": "read"},
      109,
      {"class": "duration", "value": 316},
      {"class": "duration", "value": 5774},
      {"class": "unknown"},
      {"class": "duration", "value": 9277}
    ]
  ]
}
```

**Example** (dynamic title):

```json
{
  "time-range": {
    "class": "time-range",
    "begin": 1444334398154194201,
    "end": 1444334425194487548
  },
  "class": {
    "inherit": "some-latency",
    "title": "Latency of my stuff [42, 19, -3]"
  },
  "data": [
    [
      {"class": "syscall", "name": "open"},
      45,
      {"class": "duration", "value": 5562},
      {"class": "duration", "value": 13835},
      {"class": "duration", "value": 77683},
      {"class": "duration", "value": 15263}
    ],
    [
      {"class": "syscall", "name": "read"},
      109,
      {"class": "duration", "value": 316},
      {"class": "duration", "value": 5774},
      {"class": "unknown"},
      {"class": "duration", "value": 9277}
    ]
  ]
}
```

**Example** (dynamic column descriptions):

```json
{
  "time-range": {
    "class": "time-range",
    "begin": 1444334398154194201,
    "end": 1444334425194487548
  },
  "class": {
    "title": "System call stuff for process zsh [4723]",
    "column-descriptions": [
      {
        "title": "System call involved",
        "class": "syscall"
      },
      {
        "title": "Count in region AX:23",
        "class": "int"
      },
      {
        "title": "Count in region BC:86",
        "class": "int"
      },
      {
        "title": "Count in region HE:37",
        "class": "int"
      }
    ]
  },
  "data": [
    [
      {
        "class": "syscall",
        "name": "read"
      },
      19,
      155,
      2
    ],
    [
      {
        "class": "syscall",
        "name": "write"
      },
      45,
      192,
      17
    ]
  ]
}
```


#### Analysis results object

An _analysis results object_ contains the actual data outputted by the
analysis.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `results` | Array of [result table objects](#result-table-object) | Analysis results tables | Yes (at least one table) | N/A |

**Example**:

```json
{
  "results": [
    {
      "time-range": {
        "class": "time-range",
        "begin": 1444334398154194201,
        "end": 1444334425194487548
      },
      "class": "syscall-latency",
      "data": [
        [
          {"class": "syscall", "name": "open"},
          45,
          {"class": "duration", "value": 5562},
          {"class": "duration", "value": 13835},
          {"class": "duration", "value": 77683},
          {"class": "duration", "value": 15263}
        ],
        [
          {"class": "syscall", "name": "read"},
          109,
          {"class": "duration", "value": 316},
          {"class": "duration", "value": 5774},
          {"class": "unknown"},
          {"class": "duration", "value": 9277}
        ]
      ]
    },
    {
      "time-range": {
        "class": "time-range",
        "begin": 1444334425194487549,
        "end": 1444334425254887190
      },
      "class": "syscall-latency",
      "data": [
        [
          {"class": "syscall", "name": "open"},
          45,
          {"class": "duration", "value": 1578},
          {"class": "duration", "value": 16648},
          {"class": "duration", "value": 15444},
          {"class": "duration", "value": 68540}
        ],
        [
          {"class": "syscall", "name": "read"},
          109,
          {"class": "duration", "value": 78},
          {"class": "duration", "value": 1948},
          {"class": "duration", "value": 11184},
          {"class": "duration", "value": 94670}
        ]
      ]
    }
  ]
}
```
