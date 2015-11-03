# LTTng analyses machine interface

This document explains the input and output of the LTTng analyses'
**machine interface**.

The LTTng analyses project is a set of scripts which analyze one or more
traces and output the results of this analysis. Each script is responsible
for one analysis.


## Input format

There are two different phases. The client first gets the static metadata
of the analysis, then the client can perform as many analyses as needed
on different time ranges using this metadata.

The input format of the LTTng analyses MI scripts is a list of standard
command-line arguments.

**Metadata phase**:

| Argument | Description | Default |
|---|---|---|
| `--metadata` | Output the analysis' metadata instead of analyzing | N/A |

**Analysis phase**:

| Argument | Description | Default |
|---|---|---|
| 1st positional | Path to trace(s) to analyze | N/A |
| `--begin` | Beginning timestamp of analysis (ns) | Absolute beginning of the analyzed traces |
| `--end` | End timestamp of analysis (ns) | Absolute end of the analyzed traces |
| `--limit` | Maximum number of output rows per result table or `unlimited` | `unlimited` |


## Output format

The output format is always UTF-8 [JSON](http://json.org/).

There are two different output phases. The client should first get the
analysis' metadata by running:

    script --metadata

where `script` is the script containing the analysis. This is know as the
[metadata phase](#metadata). This output provides everything about the analysis
which is not result data: analysis title, authors, description, result table
column classes/titles/units, etc.

Then, the client can perform as many analyses as required by running the script
with the mandatory trace path argument. This is known
as the [analysis phase](#analysis).

Note that any [result table](#result-table) can still provide a dynamic table class
object along with the data when, for example, dynamic columns are required.


### Data objects

_Data objects_ contain data of specific classes.

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


#### Unknown object

The special _unknown object_ represents an unknown value. It is
typically used in result table cells where a given computation cannot
produce a result for some reason.

This object has no properties.

**Example**:

```json
{
  "class": "unknown"
}
```


#### Ratio object

A _ratio object_ describes a simple, dimensionless ratio, that is,
a relationship between two quantities having the same unit indicating
how many times the first quantity contains the second.

It is suggested that the client shows a ratio object as a percentage.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `value` | Number | Ratio as a decimal fraction | Yes | N/A |

**Example**:

```json
{
  "class": "ratio",
  "value": 0.57
}
```


#### Timestamp object

A _timestamp object_ describes a specific point in time.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `value` | Number | Number of nanoseconds since Unix epoch | Yes | N/A |

**Example**:

```json
{
  "class": "timestamp",
  "value": 1444334398154194201
}
```


#### Time range object

A _time range object_ describes an interval bounded by two point in
time.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
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


#### Duration object

A _duration object_ describes the difference between two points in time.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `value` | Number | Time duration in nanoseconds | Yes | N/A |

**Example**:

```json
{
  "class": "duration",
  "value": 917238723
}
```


#### Size object

A _size object_ describes the size of a file, of a buffer, of a transfer, etc.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `value` | Integer | Size in bytes | Yes | N/A |

**Example**:

```json
{
  "class": "size",
  "value": 4994857
}
```


#### Bitrate object

A _bitrate object_ describes a transfer rate.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `value` | Number | Bitrate in bits/second | Yes | N/A |

**Example**:

```json
{
  "class": "bitrate",
  "value": 9845154
}
```


#### Syscall object

A _syscall object_ describes the name of a system call.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `name` | String | System call name | Yes | N/A |

**Example**:

```json
{
  "class": "syscall",
  "name": "write"
}
```


#### Process object

A _process object_ describes a system process.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
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


#### Path object

A _path object_ describes a relative or absolute file system path.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `path` | String | File system path | Yes | N/A |

**Example**:

```json
{
  "class": "path",
  "path": "/usr/bin/grep"
}
```


#### File descriptor object

A _file descriptor object_ describes the numeric descriptor of a file.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `fd` | Integer | File descriptor | Yes | N/A |

**Example**:

```json
{
  "class": "fd",
  "fd": 8
}
```


#### IRQ object

An _IRQ object_ describes an interrupt source.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
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


#### CPU object

A _CPU object_ describes a numeric CPU identifier.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `id` | Integer | CPU identifier number | Yes | N/A |

**Example**:

```json
{
  "class": "cpu",
  "id": 1
}
```


#### Disk object

A _disk object_ describes a disk name.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `name` | String | Disk name | Yes | N/A |

**Example**:

```json
{
  "class": "disk",
  "name": "sda"
}
```


#### Disk partition object

A _disk partition object_ describes a disk partition name.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `name` | String | Disk partition name | Yes | N/A |

**Example**:

```json
{
  "class": "part",
  "name": "sdb2"
}
```


#### Network interface object

A _network interface object_ describes a network interface name.

**Properties**:

| Property | Type | Description | Required? | Default value |
|---|---|---|---|---|
| `name` | String | Network interface name | Yes | N/A |

**Example**:

```json
{
  "class": "netif",
  "name": "eth0"
}
```


### Metadata

The _metadata phase_ explains the analysis. It provides an optional title for the
analysis and the format of the result tables (outputted in the
[analysis phase](#analysis) by the same analysis).

The metadata phase writes a [metadata object](#metadata-object).


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
| `version` | [Version object](#version-object) | Version of the analysis | No | No version |
| `title` | String | Analysis title | No | No title |
| `authors` | Array of strings | Author(s) of the analysis | No | No authors |
| `description` | String | Analysis description | No | No description |
| `url` | String | URL where to find the analysis | No | No URL |
| `tags` | Array of strings | List of tags associated with the analysis | No | No tags |
| `table-classes` | Object mapping table class names (strings) to [table class objects](#table-class-object) | Classes of potential result tables | Yes (at least one table class) | N/A |

The `table-classes` property describes all the potential result
tables with a static layout that can be generated by the
[analysis phase](#analysis). A result table can specify the name
of its table class, or define a full table class in place for
dynamic result tables.

**Example**:

```json
{
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

The _analysis phase_ outputs the actual data of the analysis.

The analysis phase writes an [analysis results object](#analysis-results-object).


#### Result table object

A _result table object_ represents the data of an analysis in rows
and columns.

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
property of the associated [column description object](#column-description-object).

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
