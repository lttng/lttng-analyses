# The MIT License (MIT)
#
# Copyright (C) 2016 - Julien Desfossez <jdesfossez@efficios.com>
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

import sys
import math
import operator
import statistics
import collections
import ast
from . import mi, termgraph
from ..core import periods
from .command import Command


_PeriodStats = collections.namedtuple('_PeriodStats', [
    'count',
    'min',
    'max',
    'stdev',
    'total',
])


class _AggregatedItem():
    def __init__(self, event, parent_event, group_by_captures, full_captures):
        self._event = event
        self._parent = parent_event
        self._group_by_captures = group_by_captures
        self._full_captures = full_captures

    @property
    def event(self):
        return self._event

    @property
    def parent_event(self):
        return self._parent

    @property
    def group_by_captures(self):
        return self._group_by_captures

    @property
    def full_captures(self):
        return self._full_captures


class PeriodAnalysisCommand(Command):
    _DESC = """The periods command."""
    _ANALYSIS_CLASS = periods.PeriodAnalysis
    _MI_TITLE = 'Periods analysis'
    _MI_DESCRIPTION = \
        'Periods frequency distribution, statistics, top, and log'
    _MI_TAGS = [mi.Tags.PERIOD, mi.Tags.STATS, mi.Tags.FREQ, mi.Tags.TOP,
                mi.Tags.LOG]
    _MI_TABLE_CLASS_LOG = 'log'
    _MI_TABLE_CLASS_TOP = 'top'
    _MI_TABLE_CLASS_TOTAL_STATS = 'total_stats'
    _MI_TABLE_CLASS_PER_PERIOD_STATS = 'per_period_stats'
    _MI_TABLE_CLASS_FREQ = 'freq'
    _MI_TABLE_CLASS_HIERARCHICAL_LOG = 'aggregated_log'
    _MI_TABLE_CLASS_AGGREGATED_TOP = 'aggregated_top'
    _MI_TABLE_CLASS_AGGREGATED_STATS = 'aggregated_stats'
    _MI_TABLE_CLASSES = [
        (
            _MI_TABLE_CLASS_LOG,
            'Period log', [
                ('begin_ts', 'Period begin timestamp', mi.Timestamp),
                ('end_ts', 'Period end timestamp', mi.Timestamp),
                ('duration', 'Period duration', mi.Duration),
                ('name', 'Period name', mi.String),
                ('begin_captures', 'Begin captures', mi.String),
                ('end_captures', 'End captures', mi.String),
            ]
        ),
        (
            _MI_TABLE_CLASS_TOP,
            'Period top', [
                ('begin_ts', 'Period begin timestamp', mi.Timestamp),
                ('end_ts', 'Period end timestamp', mi.Timestamp),
                ('duration', 'Period duration', mi.Duration),
                ('name', 'Period name', mi.String),
                ('begin_captures', 'Begin captures', mi.String),
                ('end_captures', 'End captures', mi.String),
            ]
        ),
        (
            _MI_TABLE_CLASS_TOTAL_STATS,
            'Period statistics', [
                ('count', 'Period count', mi.Number, 'occurences'),
                ('min_duration', 'Minimum duration', mi.Duration),
                ('avg_duration', 'Average duration', mi.Duration),
                ('max_duration', 'Maximum duration', mi.Duration),
                ('stdev_duration', 'Period duration standard deviation',
                 mi.Duration),
            ]
        ),
        (
            _MI_TABLE_CLASS_PER_PERIOD_STATS,
            'Period statistics', [
                ('name', 'Period name', mi.String),
                ('count', 'Period count', mi.Number, 'occurences'),
                ('min_duration', 'Minimum duration', mi.Duration),
                ('avg_duration', 'Average duration', mi.Duration),
                ('max_duration', 'Maximum duration', mi.Duration),
                ('stdev_duration', 'Period duration standard deviation',
                 mi.Duration),
            ]
        ),
        (
            _MI_TABLE_CLASS_FREQ,
            'Period duration frequency distribution', [
                ('duration_lower', 'Duration (lower bound)', mi.Duration),
                ('duration_upper', 'Duration (upper bound)', mi.Duration),
                ('count', 'Period count', mi.Number, 'occurences'),
            ]
        ),
        (
            _MI_TABLE_CLASS_HIERARCHICAL_LOG,
            'Hierarchical period log', [
                ('parent_begin_ts', 'Parent begin timestamp', mi.Timestamp),
                ('parent_end_ts', 'Parent end timestamp', mi.Timestamp),
                ('parent_name', 'Parent period name', mi.String),
                ('child_begin_ts', 'Child begin timestamp', mi.Timestamp),
                ('child_end_ts', 'Child end timestamp', mi.Timestamp),
                ('child_name', 'Child period name', mi.String),
                ('child_duration', 'Child period duration', mi.Duration),
                ('parent_duration', 'Parent period duration', mi.Duration),
                ('captures', 'Captures', mi.String),
            ]
        ),
        (
            _MI_TABLE_CLASS_AGGREGATED_TOP,
            'Aggregated period top', [
                ('parent_begin_ts', 'Parent begin timestamp', mi.Timestamp),
                ('parent_end_ts', 'Parent end timestamp', mi.Timestamp),
                ('parent_name', 'Parent period name', mi.String),
                ('child_begin_ts', 'Child begin timestamp', mi.Timestamp),
                ('child_end_ts', 'Child end timestamp', mi.Timestamp),
                ('child_name', 'Child period name', mi.String),
                ('child_duration', 'Child period duration', mi.Duration),
                ('parent_duration', 'Parent period duration', mi.Duration),
                ('captures', 'Captures', mi.String),
            ]
        ),
        (
            _MI_TABLE_CLASS_AGGREGATED_STATS,
            'Aggregated period statistics', [
                ('parent_name', 'Parent period name', mi.String),
                ('parent_begin_ts', 'Parent begin timestamp', mi.Timestamp),
                ('parent_end_ts', 'Parent end timestamp', mi.Timestamp),
                ('child_name', 'Child period name', mi.String),
                ('count', 'Period count', mi.Number, 'occurences'),
                ('min_duration', 'Minimum duration', mi.Duration),
                ('avg_duration', 'Average duration', mi.Duration),
                ('max_duration', 'Maximum duration', mi.Duration),
                ('stdev_duration', 'Period duration standard deviation',
                 mi.Duration),
            ]
        ),
    ]

    def _get_count(self, period_event):
        pass

    def _filter_duration(self, period_event):
        if self._args.min_duration is not None and \
                period_event.duration < (self._args.min_duration * 1000):
            return False
        if self._args.max_duration is not None and \
                period_event.duration > (self._args.max_duration * 1000):
            return False
        return True

    def _analysis_tick(self, period_data, end_ns):
        # We only output something at the end of the analysis
        # not when each period finishes
        if period_data is not None:
            return

        # Override the timestamps since we are only interested in the
        # whole analysis timestamps, not the ones from the last period.
        begin_ns = self._analysis.first_event_ts
        end_ns = self._analysis.last_event_ts
        log_table = None
        top_table = None
        total_stats_table = None
        per_period_stats_table = None
        total_freq_tables = None
        per_period_freq_tables = None

        aggregated_list = None
        group_dict = None
        hierarchical_list = None
        hierarchical_log_tables = None
        hierarchical_top_tables = None
        aggregated_stats_tables = None
        per_parent_aggregated_dict = None

        if self._args.select or self._args.order_by == "hierarchy":
            aggregated_list, per_parent_aggregated_dict, hierarchical_list = \
                self._get_aggregated_list()
            if self._args.group_by:
                group_dict = self._get_groups_dict(aggregated_list)

        if self._args.log:
            if self._args.order_by == "hierarchy":
                log_table = self._get_log_result_table(
                    begin_ns, end_ns, hierarchical_list)
            else:
                log_table = self._get_log_result_table(
                    begin_ns, end_ns, self._analysis.all_period_list)

        if self._args.top:
            top_table = self._get_top_result_table(
                begin_ns, end_ns, self._analysis.all_period_list)

        if self._args.stats:
            if per_parent_aggregated_dict is not None:
                aggregated_stats_tables = \
                    self._get_aggregated_stats_table(
                        begin_ns, end_ns,
                        per_parent_aggregated_dict, group_dict,
                        top=True)
            else:
                if self._args.total:
                    total_stats_table = self._get_total_stats_result_table(
                        begin_ns, end_ns)

                if self._args.per_period:
                    per_period_stats_table = \
                        self._get_per_period_stats_result_table(begin_ns,
                                                                end_ns)

        if self._args.freq:
            if self._args.total:
                total_freq_tables = self._get_total_freq_result_tables(
                    begin_ns, end_ns)

            if self._args.per_period:
                per_period_freq_tables = \
                    self._get_per_period_freq_result_tables(begin_ns, end_ns)

        if self._mi_mode:
            if log_table:
                self._mi_append_result_table(log_table)

            if top_table:
                self._mi_append_result_table(top_table)

            if total_stats_table and total_stats_table.rows:
                self._mi_append_result_table(total_stats_table)

            if per_period_stats_table and per_period_stats_table.rows:
                self._mi_append_result_table(per_period_stats_table)

            if self._args.freq:
                if total_freq_tables:
                    self._mi_append_result_tables(total_freq_tables)

                if per_period_freq_tables:
                    self._mi_append_result_tables(per_period_freq_tables)
        else:
            self._print_date(begin_ns, end_ns)

            if self._args.stats:
                if total_stats_table:
                    self._print_total_stats(total_stats_table)
                if per_period_stats_table:
                    self._print_per_period_stats(per_period_stats_table)

            if self._args.freq:
                if total_freq_tables:
                    self._print_freq(total_freq_tables)
                if per_period_freq_tables:
                    self._print_freq(per_period_freq_tables)

            if log_table:
                self._print_period_events(log_table)

            if top_table:
                self._print_period_events(top_table)

            if hierarchical_log_tables:
                self._print_aggregated_period_events(hierarchical_log_tables)

            if hierarchical_top_tables:
                self._print_aggregated_period_events(hierarchical_top_tables)

            if aggregated_stats_tables:
                self._print_aggregated_period_stats(aggregated_stats_tables)

    def _get_filtered_min_max_count_avg_total_flist(self, period_list):
        min = None
        max = None
        count = 0
        avg = 0
        total = 0
        filter_list = []
        for period_event in period_list:
            if not self._filter_duration(period_event):
                continue
            if min is None or min > period_event.duration:
                min = period_event.duration
            if max is None or max < period_event.duration:
                max = period_event.duration
            count += 1
            total += period_event.duration
            filter_list.append(period_event)
        if count > 0:
            avg = total / count
        else:
            avg = 0
        return min, max, count, avg, total, filter_list

    def _get_agg_filtered_min_max_count_avg_total_flist(self, ag_list):
        min = None
        max = None
        count = 0
        avg = 0
        total = 0
        filter_list = []
        for ag_event in ag_list:
            period_event = ag_event.event
            if not self._filter_duration(period_event):
                continue
            if min is None or min > period_event.duration:
                min = period_event.duration
            if max is None or max < period_event.duration:
                max = period_event.duration
            count += 1
            total += period_event.duration
            filter_list.append(period_event)
        if count > 0:
            avg = total / count
        else:
            avg = 0
        return min, max, count, avg, total, filter_list

    def _find_aggregated_subperiods(self, root, event, aggregated_list,
                                    group_by_captures,
                                    full_captures):
        if len(self._analysis_conf._select) == 0 or \
                event.name in self._analysis_conf._select:
            aggregated_list.append(_AggregatedItem(event, root,
                                                   group_by_captures,
                                                   full_captures))
        for capture in event.filtered_captures(
                self._analysis_conf._group_by):
            group_by_captures.append(capture)
        for capture in event.full_captures():
            full_captures.append(capture)
        for child in event.children:
            self._find_aggregated_subperiods(root, child,
                                             aggregated_list,
                                             group_by_captures,
                                             full_captures)

    def _hierarchical_sub(self, tmp_list, event):
        tmp_list.append(event)
        for child in event.children:
            self._hierarchical_sub(tmp_list, child)

    def _get_aggregated_list(self):
        # List of _AggregatedItem
        aggregated_list = []
        # Dict with parent period as key. Each entry contains a dict
        # of all child period that each contain a list of _AggregatedItem.
        # parent_aggregated_dict[parent_period][child_period] = []
        parent_aggregated_dict = {}
        # List of PeriodEvent ordered in hierarchy (parents are followed
        # by their children)
        hierarchical_list = []
        for period_event in self._analysis.all_period_list:
            if self._analysis_conf._order_by == "hierarchy":
                # Only top-level events
                if period_event.parent is None:
                    hierarchical_list.append(period_event)
                    for child in period_event.children:
                        tmp_list = []
                        self._hierarchical_sub(tmp_list, child)
                        for item in tmp_list:
                            hierarchical_list.append(item)

            if period_event.name != self._analysis_conf._aggregate_by:
                continue
            if not self._filter_duration(period_event):
                continue
            if period_event not in parent_aggregated_dict.keys():
                parent_aggregated_dict[period_event] = {}
            tmp_list = []
            for child in period_event.children:
                self._find_aggregated_subperiods(
                    period_event,
                    child, tmp_list,
                    period_event.filtered_captures(
                        self._analysis_conf._group_by),
                    period_event.full_captures())
            for item in tmp_list:
                aggregated_list.append(item)
                if item.event.name not in \
                        parent_aggregated_dict[period_event].keys():
                    parent_aggregated_dict[period_event][item.event.name] = []
                parent_aggregated_dict[period_event][item.event.name]. \
                    append(item)
        ordered_parent = collections.OrderedDict(
            sorted(parent_aggregated_dict.items(),
                   key=lambda t: t[0].start_ts))
        return aggregated_list, ordered_parent, hierarchical_list

    def _get_groups_dict(self, aggregated_list):
        # Dict of groups, each item contains the list of _AggregatedItem that
        # have the same group key (sorted list of all possible group-by values)
        groups = {}
        for ag_event in aggregated_list:
            group_key = ""
            for group in sorted(ag_event.group_by_captures,
                                key=lambda x: x[0]):
                if len(group_key) == 0:
                    group_key = "%s = %s" % (group[0], group[1])
                else:
                    group_key = "%s, %s = %s" % (group_key, group[0], group[1])

            if group_key not in groups.keys():
                groups[group_key] = []
            groups[group_key].append(ag_event)
        return groups

    def _get_total_period_lists_stats(self):
        if self._args.min_duration is None and \
                self._args.max_duration is None:
            total_list = self._analysis.all_period_list
            stdev = self._compute_period_duration_stdev(total_list)
            total_stats = _PeriodStats(
                count=self._analysis.all_count,
                min=self._analysis.all_min_duration,
                max=self._analysis.all_max_duration,
                stdev=stdev,
                total=self._analysis.all_total_duration
            )
        else:
            min, max, count, avg, total, total_list = \
                self._get_filtered_min_max_count_avg_total_flist(
                    self._analysis.all_period_list)
            total_stats = _PeriodStats(
                count=count,
                min=min,
                max=max,
                stdev=self._compute_period_duration_stdev(total_list),
                total=total,
            )

        return [total_list], total_stats

    def _get_one_hierarchical_log_table(self, begin_ns, end_ns,
                                        aggregated_list, sub, top):
        if top:
            table = self._mi_create_result_table(
                self._MI_TABLE_CLASS_AGGREGATED_TOP, begin_ns, end_ns,
                subtitle=sub)
            top_events = sorted(aggregated_list, key=operator.attrgetter(
                'event.duration'), reverse=True)
            top_events = top_events[:self._args.limit]
            for ag_event in top_events:
                table.append_row(
                    parent_begin_ts=mi.Timestamp(
                        ag_event.parent_event.start_ts),
                    parent_end_ts=mi.Timestamp(
                        ag_event.parent_event.end_ts),
                    parent_name=mi.String(ag_event.parent_event.name),
                    child_begin_ts=mi.Timestamp(ag_event.event.start_ts),
                    child_end_ts=mi.Timestamp(ag_event.event.end_ts),
                    child_name=mi.String(ag_event.event.name),
                    child_duration=mi.Duration(ag_event.event.duration),
                    parent_duration=mi.Duration(
                        ag_event.parent_event.duration),
                    captures=mi.String(str(ag_event.full_captures)),
                )
        else:
            table = self._mi_create_result_table(
                self._MI_TABLE_CLASS_HIERARCHICAL_LOG, begin_ns, end_ns,
                subtitle=sub)
            for ag_event in aggregated_list:
                table.append_row(
                    parent_begin_ts=mi.Timestamp(
                        ag_event.parent_event.start_ts),
                    parent_end_ts=mi.Timestamp(ag_event.parent_event.end_ts),
                    parent_name=mi.String(ag_event.parent_event.name),
                    child_begin_ts=mi.Timestamp(ag_event.event.start_ts),
                    child_end_ts=mi.Timestamp(ag_event.event.end_ts),
                    child_name=mi.String(ag_event.event.name),
                    child_duration=mi.Duration(ag_event.event.duration),
                    parent_duration=mi.Duration(
                        ag_event.parent_event.duration),
                    captures=mi.String(str(ag_event.full_captures)),
                )
        return table

    def _get_hierarchical_log_top_result_table(self, begin_ns, end_ns,
                                               aggregated_list, group_dict,
                                               top=False):
        result_tables = []
        ag_list = ""
        for i in self._analysis_conf._select:
            if len(ag_list) == 0:
                ag_list = i
            else:
                ag_list = "%s, %s" % (ag_list, i)
        sub = "Aggregation of (%s) by %s" % (
            ag_list, self._analysis_conf._aggregate_by)

        if group_dict is None:
            table = self._get_one_hierarchical_log_table(begin_ns, end_ns,
                                                         aggregated_list, sub,
                                                         top)
            result_tables.append(table)
        else:
            for group in group_dict.keys():
                group_sub = "%s, group: %s" % (sub, group)
                result_tables.append(self._get_one_hierarchical_log_table(
                    begin_ns, end_ns, group_dict[group], group_sub, top))

        return result_tables

    def _get_full_period_path(self, period_event):
        return self._analysis_conf.period_def_registry.period_full_path(
            period_event.name)

    def _get_log_result_table(self, begin_ns, end_ns, period_list):
        result_table = self._mi_create_result_table(self._MI_TABLE_CLASS_LOG,
                                                    begin_ns, end_ns)
        for period_event in period_list:
            if not self._filter_duration(period_event):
                continue
            result_table.append_row(
                begin_ts=mi.Timestamp(period_event.start_ts),
                end_ts=mi.Timestamp(period_event.end_ts),
                duration=mi.Duration(period_event.duration),
                name=mi.String(self._get_full_period_path(period_event)),
                begin_captures=mi.String(period_event.begin_captures),
                end_captures=mi.String(period_event.end_captures),
            )
        return result_table

    def _get_top_result_table(self, begin_ns, end_ns, event_list):
        result_table = self._mi_create_result_table(
            self._MI_TABLE_CLASS_TOP, begin_ns, end_ns)

        top_events = sorted(event_list,
                            key=operator.attrgetter('duration'),
                            reverse=True)
        top_events = top_events[:self._args.limit]

        for period_event in top_events:
            if not self._filter_duration(period_event):
                continue
            result_table.append_row(
                begin_ts=mi.Timestamp(period_event.start_ts),
                end_ts=mi.Timestamp(period_event.end_ts),
                duration=mi.Duration(period_event.duration),
                name=mi.String(period_event.name),
                begin_captures=mi.String(period_event.begin_captures),
                end_captures=mi.String(period_event.end_captures),
            )
        return result_table

    def _get_total_stats_result_table(self, begin_ns, end_ns):
        stats_table = \
            self._mi_create_result_table(self._MI_TABLE_CLASS_TOTAL_STATS,
                                         begin_ns, end_ns)

        if self._args.min_duration is None and \
                self._args.max_duration is None:
            stdev = self._compute_period_duration_stdev(
                self._analysis.all_period_list)
            count = self._analysis.all_count
            min = self._analysis.all_min_duration
            max = self._analysis.all_max_duration
            if count == 0:
                avg = 0
            else:
                avg = self._analysis.all_total_duration / \
                    self._analysis.all_count
        else:
            min, max, count, avg, total, period_list = \
                self._get_filtered_min_max_count_avg_total_flist(
                    self._analysis.all_period_list)
            stdev = self._compute_period_duration_stdev(period_list)

        if math.isnan(stdev):
            stdev = mi.Unknown()
        else:
            stdev = mi.Duration(stdev)

        avg = mi.Duration(avg)
        if min is None:
            min = mi.Duration(0)
        else:
            min = mi.Duration(min)

        if max is None:
            max = mi.Duration(0)
        else:
            max = mi.Duration(max)

        stats_table.append_row(
            count=mi.Number(count),
            min_duration=min,
            avg_duration=avg,
            max_duration=max,
            stdev_duration=stdev,
        )

        return stats_table

    def _get_per_period_stats_result_table(self, begin_ns, end_ns):
        stats_table = \
            self._mi_create_result_table(self._MI_TABLE_CLASS_PER_PERIOD_STATS,
                                         begin_ns, end_ns)

        period_stats_list = sorted(list(
            self._analysis.all_period_stats.values()),
            key=lambda period: period.name.lower())

        for period_stats in period_stats_list:
            if not period_stats.period_list:
                continue

            if self._args.min_duration is None and \
                    self._args.max_duration is None:
                stdev = self._compute_period_duration_stdev(
                    period_stats.period_list)
                min = period_stats.min_duration
                max = period_stats.max_duration
                count = period_stats.count
                if count > 0:
                    avg = period_stats.total_duration / \
                        period_stats.count
                else:
                    avg = 0
            else:
                min, max, count, avg, total, period_list = \
                    self._get_filtered_min_max_count_avg_total_flist(
                        period_stats.period_list)
                stdev = self._compute_period_duration_stdev(period_list)

            if math.isnan(stdev):
                stdev = mi.Unknown()
            else:
                stdev = mi.Duration(stdev)

            stats_table.append_row(
                name=mi.String(period_stats.name),
                count=mi.Number(count),
                min_duration=mi.Duration(min),
                avg_duration=mi.Duration(avg),
                max_duration=mi.Duration(max),
                stdev_duration=stdev,
            )

        return stats_table

    def _get_one_aggregated_stats_table(self, begin_ns, end_ns,
                                        per_parent_aggregated_dict, sub, top):
        table = self._mi_create_result_table(
            self._MI_TABLE_CLASS_AGGREGATED_STATS, begin_ns, end_ns,
            subtitle=sub)
        for parent_period in per_parent_aggregated_dict.keys():
            for child_period in \
                    per_parent_aggregated_dict[parent_period].keys():
                child_period_list = \
                    per_parent_aggregated_dict[parent_period][child_period]
                min, max, count, avg, total, period_list = \
                    self._get_agg_filtered_min_max_count_avg_total_flist(
                        child_period_list)
                stdev = self._compute_period_agg_duration_stdev(
                    child_period_list)

                if math.isnan(stdev):
                    stdev = mi.Unknown()
                else:
                    stdev = mi.Duration(stdev)

                table.append_row(
                    parent_begin_ts=mi.Timestamp(
                        parent_period.start_ts),
                    parent_end_ts=mi.Timestamp(
                        parent_period.end_ts),
                    parent_name=mi.String(parent_period.name),
                    child_name=mi.String(child_period),
                    count=mi.Number(count),
                    min_duration=mi.Duration(min),
                    avg_duration=mi.Duration(avg),
                    max_duration=mi.Duration(max),
                    stdev_duration=stdev,
                )
        return table

    def _get_aggregated_stats_table(self, begin_ns, end_ns,
                                    per_parent_aggregated_dict, group_dict,
                                    top=False):
        result_tables = []
        ag_list = ""
        for i in self._analysis_conf._select:
            if len(ag_list) == 0:
                ag_list = i
            else:
                ag_list = "%s, %s" % (ag_list, i)
        sub = "Aggregation of (%s) by %s" % (
            ag_list, self._analysis_conf._aggregate_by)

        if group_dict is None:
            table = self._get_one_aggregated_stats_table(
                begin_ns, end_ns, per_parent_aggregated_dict, sub, top)
            result_tables.append(table)
        else:
            # TODO
            for group in group_dict.keys():
                group_sub = "%s, group: %s" % (sub, group)
                result_tables.append(self._get_one_aggregated_stats_table(
                    begin_ns, end_ns, group_dict[group], group_sub, top))

        return result_tables

    def _fill_freq_result_table(self, period_list, stats, min_duration,
                                max_duration, step, freq_table):
        # The number of bins for the histogram
        resolution = self._args.freq_resolution

        if not self._args.freq_uniform:
            if self._args.min is not None:
                min_duration = self._args.min
            else:
                min_duration = stats.min

            if self._args.max is not None:
                max_duration = self._args.max
            else:
                max_duration = stats.max

            # ns to µs
            if min_duration is None:
                min_duration = 0
            else:
                min_duration /= 1000

            if max_duration is None:
                max_duration = 0
            else:
                max_duration /= 1000

            step = (max_duration - min_duration) / resolution

        if step == 0:
            return

        buckets = []
        counts = []

        for i in range(resolution):
            buckets.append(i * step)
            counts.append(0)

        for period_event in period_list:
            if not self._filter_duration(period_event):
                continue
            duration = period_event.duration / 1000
            index = int((duration - min_duration) / step)

            if index >= resolution:
                # special case for max value: put in last bucket (includes
                # its upper bound)
                if duration == max_duration:
                    counts[index - 1] += 1

                continue

            counts[index] += 1

        for index, count in enumerate(counts):
            lower_bound = index * step + min_duration
            upper_bound = (index + 1) * step + min_duration
            freq_table.append_row(
                duration_lower=mi.Duration.from_us(lower_bound),
                duration_upper=mi.Duration.from_us(upper_bound),
                count=mi.Number(count),
            )

    def _get_total_freq_result_tables(self, begin_ns, end_ns):
        freq_tables = []
        period_lists, period_stats = self._get_total_period_lists_stats()
        min_duration = None
        max_duration = None
        step = None
        subtitle = 'All periods'

        if self._args.freq_uniform:
            durations = []

            for period_list in period_lists:
                for period_event in period_list:
                    if not self._filter_duration(period_event):
                        continue
                    durations.append(period_event.duration)

            min_duration, max_duration, step = \
                self._get_uniform_freq_values(durations)

        for period_list in period_lists:
            freq_table = \
                self._mi_create_result_table(self._MI_TABLE_CLASS_FREQ,
                                             begin_ns, end_ns, subtitle)
            self._fill_freq_result_table(period_list, period_stats,
                                         min_duration, max_duration, step,
                                         freq_table)
            freq_tables.append(freq_table)

        return freq_tables

    def _get_period_lists_stats(self):
        period_lists = {}
        period_stats = {}

        for period in self._analysis.all_period_stats.keys():
            period_list = self._analysis.all_period_stats[period].period_list

            if not period_list:
                continue
            if self._args.min_duration is None and \
                    self._args.max_duration is None:
                stdev = self._compute_period_duration_stdev(period_list)
                count = len(period_list)
                min = self._analysis.all_period_stats[period].min_duration
                max = self._analysis.all_period_stats[period].max_duration
                total = \
                    self._analysis.all_period_stats[period].total_duration
            else:
                min, max, count, avg, total, period_list = \
                    self._get_filtered_min_max_count_avg_total_flist(
                        period_list)
                stdev = self._compute_period_duration_stdev(period_list)

            period_stats[period] = _PeriodStats(
                count=count,
                min=min,
                max=max,
                stdev=stdev,
                total=total,
            )
            period_lists[period] = period_list

        return period_lists, period_stats

    def _get_per_period_freq_result_tables(self, begin_ns, end_ns):
        freq_tables = []
        period_lists, period_stats = self._get_period_lists_stats()
        min_duration = None
        max_duration = None
        step = None

        if self._args.freq_uniform:
            durations = []

            for period_list in period_lists.values():
                for period_event in period_list:
                    if not self._filter_duration(period_event):
                        continue
                    durations.append(period_event.duration)

            min_duration, max_duration, step = \
                self._get_uniform_freq_values(durations)

        for period in sorted(period_stats.keys()):
            period_list = period_lists[period]
            stats = period_stats[period]
            subtitle = 'Period: {}'.format(period)
            freq_table = \
                self._mi_create_result_table(self._MI_TABLE_CLASS_FREQ,
                                             begin_ns, end_ns, subtitle)
            self._fill_freq_result_table(period_list, stats,
                                         min_duration, max_duration, step,
                                         freq_table)
            freq_tables.append(freq_table)

        return freq_tables

    def _compute_period_duration_stdev(self, period_events):
        period_durations = []
        for period_event in period_events:
            if not self._filter_duration(period_event):
                continue
            period_durations.append(period_event.duration)
        if len(period_durations) < 2:
            return float('nan')
        return statistics.stdev(period_durations)

    def _compute_period_agg_duration_stdev(self, period_agg_events):
        period_durations = []
        for period_event in period_agg_events:
            if not self._filter_duration(period_event.event):
                continue
            period_durations.append(period_event.event.duration)
        if len(period_durations) < 2:
            return float('nan')
        return statistics.stdev(period_durations)

    def _pop_next_capture_string(self, begin_captures, end_captures):
        if len(begin_captures.keys()) > 0:
            b_key, b_value = begin_captures.popitem()
            b_string = '%s = %s' % (b_key, b_value)
        else:
            b_string = ''

        if len(end_captures.keys()) > 0:
            e_key, e_value = end_captures.popitem()
            e_string = '%s = %s' % (e_key, e_value)
        else:
            e_string = ''

        return b_string, e_string

    def _print_period_events(self, result_table):
        fmt = '[{:<18}, {:<18}] {:>15} {:<24} {:<35} {:<35}'
        fmt_captures = '{:<18} {:<18} {:>18} {:<24} {:<35} {:<35}'
        title_fmt = '{:<20} {:<19} {:>15} {:<24} {:<35} {:<35}'
        print()
        print(result_table.title)
        print(title_fmt.format('Begin', 'End', 'Duration (us)', 'Name',
                               'Begin capture', 'End capture'))
        for row in result_table.rows:
            begin_ts = row.begin_ts.value
            end_ts = row.end_ts.value
            duration = row.duration.value
            name = row.name.value
            if name is None:
                name = ''

            # Convert back the string to dict
            begin_captures = ast.literal_eval(row.begin_captures.value)
            # Order the dict based on keys to always get the same output
            if begin_captures is None:
                begin_captures = {}
            begin_captures = collections.OrderedDict(
                sorted(begin_captures.items()))
            end_captures = ast.literal_eval(row.end_captures.value)
            if end_captures is None:
                end_captures = {}
            end_captures = collections.OrderedDict(
                sorted(end_captures.items()))

            b_string, e_string = self._pop_next_capture_string(begin_captures,
                                                               end_captures)

            print(fmt.format(self._format_timestamp(begin_ts),
                             self._format_timestamp(end_ts),
                             '%0.03f' % (duration / 1000), name,
                             b_string, e_string))

            nr_lines = max(len(begin_captures.keys()),
                           len(end_captures.keys()))
            for i in range(nr_lines):
                b_string, e_string = self._pop_next_capture_string(
                    begin_captures, end_captures)
                print(fmt_captures.format('', '', '', '', b_string, e_string))

    def _print_aggregated_period_events(self, result_tables):
        fmt = '[{:<18}, {:<18}] {:>22} {:<15} [{:<18}, {:<18}] {:>22} ' \
            '{:<15} {:<35}'
#        fmt_captures = '{:<18} {:<18} {:>25} {:<15} {:<18} {:<25} {:>18} ' \
#            '{:<15} {:<35}'
        title_fmt = '{:<20} {:<19} {:>22} {:<15} {:<20} {:<19} {:>22} ' \
            '{:<15} {:<35}'
        for result_table in result_tables:
            print()
            print(result_table.title)
            print(result_table.subtitle)
            print(title_fmt.format('Parent begin', 'Parent end',
                                   'Parent duration (us)', 'Parent name',
                                   'Child begin', 'Child end',
                                   'Child duration (us)', 'Child name',
                                   'Captures'))
            for row in result_table.rows:
                parent_begin_ts = row.parent_begin_ts.value
                parent_end_ts = row.parent_end_ts.value
                parent_duration = row.parent_duration.value
                parent_name = row.parent_name.value
                child_begin_ts = row.child_begin_ts.value
                child_end_ts = row.child_end_ts.value
                child_duration = row.child_duration.value
                child_name = row.child_name.value

                # Convert back the string to list of tuple
                captures = ast.literal_eval(row.captures.value)
                # Order the dict based on keys to always get the same output
#                if captures is None:
#                    captures = []
#                    capture_str = ''
#                else:
#                    captures = sorted(captures, key=lambda x: x[0])
#                    captures.reverse()
#                    tmp = captures.pop()
#                    capture_str = "%s = %s" % (tmp[0], tmp[1])
                capture_str = ''
                for i in sorted(captures, key=lambda x: x[0]):
                    if len(capture_str) == 0:
                        capture_str = "%s = %s" % (i[0], i[1])
                    else:
                        capture_str = "%s, %s = %s" % (capture_str, i[0], i[1])

                print(fmt.format(self._format_timestamp(parent_begin_ts),
                                 self._format_timestamp(parent_end_ts),
                                 '%0.03f' % (parent_duration / 1000),
                                 parent_name,
                                 self._format_timestamp(child_begin_ts),
                                 self._format_timestamp(child_end_ts),
                                 '%0.03f' % (child_duration / 1000),
                                 child_name,
                                 capture_str))
#                for i in range(len(captures)):
#                    tmp = captures.pop()
#                    capture_str = "%s = %s" % (tmp[0], tmp[1])
#                    print(fmt_captures.format('', '', '', '', '', '', '', '',
#                                              capture_str))

    def _print_total_stats(self, stats_table):
        row_format = '{:<12} {:<12} {:<12} {:<12} {:<12}'
        header = row_format.format(
            'Count', 'Min', 'Avg', 'Max', 'Stdev'
        )

        if stats_table.rows:
            print()
            print(stats_table.title + ' (us)')
            print(header)
            for row in stats_table.rows:
                if type(row.stdev_duration) is mi.Unknown:
                    stdev_str = '?'
                else:
                    stdev_str = '%0.03f' % row.stdev_duration.to_us()

                row_str = row_format.format(
                    '%d' % row.count.value,
                    '%0.03f' % row.min_duration.to_us(),
                    '%0.03f' % row.avg_duration.to_us(),
                    '%0.03f' % row.max_duration.to_us(),
                    '%s' % stdev_str,
                )

                print(row_str)

    def _print_per_period_stats(self, stats_table):
        row_format = '{:<25} {:>8}  {:>12}  {:>12}  {:>12}  {:>12}'
        header = row_format.format(
            'Period', 'Count', 'Min', 'Avg', 'Max', 'Stdev'
        )

        if stats_table.rows:
            print()
            print(stats_table.title + ' (us)')
            print(header)
            for row in stats_table.rows:
                if type(row.stdev_duration) is mi.Unknown:
                    stdev_str = '?'
                else:
                    stdev_str = '%0.03f' % row.stdev_duration.to_us()

                row_str = row_format.format(
                    '%s' % row.name,
                    '%d' % row.count.value,
                    '%0.03f' % row.min_duration.to_us(),
                    '%0.03f' % row.avg_duration.to_us(),
                    '%0.03f' % row.max_duration.to_us(),
                    '%s' % stdev_str,
                )

                print(row_str)

    def _print_aggregated_period_stats(self, stats_tables):
        fmt = '[{:<18}, {:<18}] {:>22} {:<15} {:<15} {:>12} {:>12} ' \
            '{:>12} {:>12} {:>12}'
        title_fmt = '{:<20} {:<19} {:>22} {:<15} {:<15} {:>12} {:>12}' \
            '{:>12} {:>12} {:>12}'
        for stats_table in stats_tables:
            print()
            print(stats_table.title)
            print(stats_table.subtitle)
            print(title_fmt.format('Parent begin', 'Parent end',
                                   'Parent duration (us)', 'Parent name',
                                   'Child name', 'Count', 'Min', 'Avg',
                                   'Max', 'Stdev'))

            for row in stats_table.rows:
                parent_begin_ts = row.parent_begin_ts.value
                parent_end_ts = row.parent_end_ts.value
                parent_duration = parent_end_ts - parent_begin_ts
                parent_name = row.parent_name.value
                child_name = row.child_name.value
                if type(row.stdev_duration) is mi.Unknown:
                    stdev_str = '?'
                else:
                    stdev_str = '%0.03f' % row.stdev_duration.to_us()

                row_str = fmt.format(
                    self._format_timestamp(parent_begin_ts),
                    self._format_timestamp(parent_end_ts),
                    '%0.03f' % (parent_duration / 1000),
                    parent_name, child_name,
                    '%d' % row.count.value,
                    '%0.03f' % row.min_duration.to_us(),
                    '%0.03f' % row.avg_duration.to_us(),
                    '%0.03f' % row.max_duration.to_us(),
                    '%s' % stdev_str,
                )

                print(row_str)

    def _print_frequency_distribution(self, freq_table):
        title_fmt = 'Periods duration frequency distribution - {}'

        graph = termgraph.FreqGraph(
            data=freq_table.rows,
            get_value=lambda row: row.count.value,
            get_lower_bound=lambda row: row.duration_lower.to_us(),
            title=title_fmt.format(freq_table.subtitle),
            unit='µs'
        )

        graph.print_graph()

    def _print_freq(self, freq_tables):
        for freq_table in freq_tables:
            self._print_frequency_distribution(freq_table)

    def _validate_transform_args(self):
        args = self._args
        self._analysis_conf._group_by = {}
        self._analysis_conf._aggregate_by = None
        self._analysis_conf._select = []
        self._analysis_conf._order_by = None

        if args.group_by:
            for group in args.group_by.split(','):
                g = group.strip()
                if len(g) == 0:
                    continue
                _period_name = g.split('.')[0]
                _period_field = g.split('.')[1]
                if _period_name not in \
                        self._analysis_conf._group_by.keys():
                    self._analysis_conf._group_by[_period_name] = []
                self._analysis_conf._group_by[_period_name]. \
                    append(_period_field)

        if args.order_by:
            if args.order_by not in ['time', 'hierarchy']:
                self._gen_error("Invalid order-by value")
            self._analysis_conf._order_by = args.order_by

        # TODO: check aggregation and group-by attributes are valid
        if args.select:
            for ag in args.select.split(','):
                self._analysis_conf._select.append(ag.strip())
        self._analysis_conf._aggregate_by = args.aggregate_by

        # Default to --per-period if no --total or aggregation parameter
        # passed
        if not (args.total or args.per_period or args.select):
            args.per_period = True

    def _add_arguments(self, ap):
        Command._add_min_max_args(ap)
        Command._add_freq_args(
            ap, help='Output statistics about periods durations')
        Command._add_top_args(ap, help='Output the top sched switch durations')
        Command._add_log_args(
            ap, help='Output the sched switches in chronological order')
        Command._add_stats_args(ap, help='Output sched switch statistics')
        ap.add_argument('--total', action='store_true',
                        help='Group all results (applies to stats and freq)')
        ap.add_argument('--per-period', action='store_true',
                        help='Group results per-period (applies to stats and '
                        'freq) (default)')
        ap.add_argument('--min-duration', type=float,
                        help='Filter out, periods shorter that duration '
                             '(usec)')
        ap.add_argument('--max-duration', type=float,
                        help='Filter out, periods longer than duration (usec)')
        ap.add_argument('--aggregate-by', type=str,
                        help='FIXME')
        ap.add_argument('--select', type=str,
                        help='FIXME')
        ap.add_argument('--group-by', type=str,
                        help='Present the results grouped by a list of fields'
                             '(period.captured_field'
                             '[, period.captured_field2])')
        ap.add_argument('--order-by', type=str,
                        help='hierarchy, time')


def _run(mi_mode):
    schedcmd = PeriodAnalysisCommand(mi_mode=mi_mode)
    schedcmd.run()


def _runstats(mi_mode):
    sys.argv.insert(1, '--stats')
    _run(mi_mode)


def _runlog(mi_mode):
    sys.argv.insert(1, '--log')
    _run(mi_mode)


def _runtop(mi_mode):
    sys.argv.insert(1, '--top')
    _run(mi_mode)


def _runfreq(mi_mode):
    sys.argv.insert(1, '--freq')
    _run(mi_mode)


def runstats():
    _runstats(mi_mode=False)


def runlog():
    _runlog(mi_mode=False)


def runtop():
    _runtop(mi_mode=False)


def runfreq():
    _runfreq(mi_mode=False)


def runstats_mi():
    _runstats(mi_mode=True)


def runlog_mi():
    _runlog(mi_mode=True)


def runtop_mi():
    _runtop(mi_mode=True)


def runfreq_mi():
    _runfreq(mi_mode=True)
