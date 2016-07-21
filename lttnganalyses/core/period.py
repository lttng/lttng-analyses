# The MIT License (MIT)
#
# Copyright (C) 2016 - Philippe Proulx <pproulx@efficios.com>
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

from . import event as core_event
from functools import partial
import babeltrace as bt
import enum


class InvalidPeriodDefinition(Exception):
    pass


# period definition registry, owner of the whole tree of periods
class PeriodDefinitionRegistry:
    def __init__(self):
        self._root_period_defs = set()
        self._named_period_defs = {}

    def has_period_def(self, name):
        return name in self._named_period_defs

    def add_period_def(self, parent_name, period_name, begin_expr, end_expr,
                       begin_captures_exprs, end_captures_exprs):
        # validate unique period name (if named)
        if self.has_period_def(period_name):
            raise InvalidPeriodDefinition('Cannot redefine period "{}"'.format(
                period_name))

        # validate that parent exists if it's set
        if parent_name is not None and not self.has_period_def(parent_name):
            fmt = 'Cannot find parent period named "{}" (as parent of ' \
                  'period "{}")'
            msg = fmt.format(parent_name, period_name)
            raise InvalidPeriodDefinition(msg)

        # create period, and associate parent and children
        parent = None

        if parent_name is not None:
            parent = self.get_period_def(parent_name)

        period_def = PeriodDefinition(parent, period_name, begin_expr,
                                      end_expr, begin_captures_exprs,
                                      end_captures_exprs)

        if parent is not None:
            parent.children.add(period_def)

        # validate new period definition
        PeriodDefinitionValidator(period_def)

        if period_def.parent is None:
            self._root_period_defs.add(period_def)

        if period_def.name is not None:
            self._named_period_defs[period_def.name] = period_def

    def get_period_def(self, name):
        return self._named_period_defs.get(name)

    @property
    def root_period_defs(self):
        for period_def in self._root_period_defs:
            yield period_def

    @property
    def is_empty(self):
        return len(self._root_period_defs) == 0 and \
                len(self._named_period_defs) == 0


# definition of a period
class PeriodDefinition:
    def __init__(self, parent, name, begin_expr, end_expr, begin_captures_exprs,
                 end_captures_exprs):
        self._parent = parent
        self._children = set()
        self._name = name
        self._begin_expr = begin_expr
        self._end_expr = end_expr
        self._begin_captures_exprs = begin_captures_exprs
        self._end_captures_exprs = end_captures_exprs

    @property
    def name(self):
        return self._name

    @property
    def parent(self):
        return self._parent

    @property
    def begin_expr(self):
        return self._begin_expr

    @property
    def end_expr(self):
        return self._end_expr

    @property
    def begin_captures_exprs(self):
        return self._begin_captures_exprs

    @property
    def end_captures_exprs(self):
        return self._end_captures_exprs

    @property
    def children(self):
        return self._children


class _Expression:
    pass


class _BinaryExpression(_Expression):
    def __init__(self, lh_expr, rh_expr):
        self._lh_expr = lh_expr
        self._rh_expr = rh_expr

    @property
    def lh_expr(self):
        return self._lh_expr

    @property
    def rh_expr(self):
        return self._rh_expr


class _UnaryExpression(_Expression):
    def __init__(self, expr):
        self._expr = expr

    @property
    def expr(self):
        return self._expr


class LogicalNot(_UnaryExpression):
    def __repr__(self):
        return '(!{})'.format(self.expr)


class LogicalAnd(_BinaryExpression):
    def __repr__(self):
        return '({} && {})'.format(self.lh_expr, self.rh_expr)


class Eq(_BinaryExpression):
    def __repr__(self):
        return '({} == {})'.format(self.lh_expr, self.rh_expr)


class Lt(_BinaryExpression):
    def __repr__(self):
        return '({} < {})'.format(self.lh_expr, self.rh_expr)


class LtEq(_BinaryExpression):
    def __repr__(self):
        return '({} <= {})'.format(self.lh_expr, self.rh_expr)


class Gt(_BinaryExpression):
    def __repr__(self):
        return '({} > {})'.format(self.lh_expr, self.rh_expr)


class GtEq(_BinaryExpression):
    def __repr__(self):
        return '({} >= {})'.format(self.lh_expr, self.rh_expr)


class Number(_Expression):
    def __init__(self, value):
        self._value = value

    @property
    def value(self):
        return self._value

    def __repr__(self):
        return '({})'.format(self.value)


class String(_Expression):
    def __init__(self, value):
        self._value = value

    @property
    def value(self):
        return self._value

    def __repr__(self):
        return '("{}")'.format(self.value)


@enum.unique
class DynScope(enum.Enum):
    AUTO = 'auto'
    TPH = '$pkt_header'
    SPC = '$pkt_ctx'
    SEH = '$header'
    SEC = '$stream_ctx'
    EC = '$ctx'
    EP = '$payload'


class _SingleChildNode(_Expression):
    def __init__(self, child):
        self._child = child

    @property
    def child(self):
        return self._child


class ParentScope(_SingleChildNode):
    def __repr__(self):
        return '$parent.{}'.format(self.child)


class BeginScope(_SingleChildNode):
    def __repr__(self):
        return '$begin.{}'.format(self.child)


class EventScope(_SingleChildNode):
    def __repr__(self):
        return '$evt.{}'.format(self.child)


class DynamicScope(_SingleChildNode):
    def __init__(self, dyn_scope, child):
        super().__init__(child)
        self._dyn_scope = dyn_scope

    @property
    def dyn_scope(self):
        return self._dyn_scope

    def __repr__(self):
        if self._dyn_scope == DynScope.AUTO:
            return repr(self.child)

        return '{}.{}'.format(self.dyn_scope.value, self.child)


class EventFieldName(_Expression):
    def __init__(self, name):
        self._name = name

    @property
    def name(self):
        return self._name

    def __repr__(self):
        return self._name


class EventName(_Expression):
    def __repr__(self):
        return '$name'


class IllegalExpression(Exception):
    pass


class PeriodDefinitionValidator:
    def __init__(self, period_def):
        self._period_def = period_def
        self._validate_expr_cbs = {
            LogicalNot: self._validate_not,
            LogicalAnd: self._validate_and_expr,
            Eq: self._validate_comp,
            Lt: self._validate_comp,
            LtEq: self._validate_comp,
            Gt: self._validate_comp,
            GtEq: self._validate_comp,
            ParentScope: self._validate_parent_scope,
        }
        self._validate_expr(period_def.begin_expr)
        self._validate_expr(period_def.end_expr)

    def _validate_not(self, not_expr):
        self._validate_expr(not_expr.expr)

    def _validate_and_expr(self, and_expr):
        self._validate_expr(and_expr.lh_expr)
        self._validate_expr(and_expr.rh_expr)

    def _validate_parent_scope(self, scope):
        if self._period_def.parent is None:
            raise IllegalExpression('Cannot refer to parent context without '
                                    'a named parent period')

        if type(scope.child) is not BeginScope:
            raise IllegalExpression('Must refer to the begin context in a '
                                    'parent context')

        self._validate_expr(scope.child)

    def _validate_comp(self, comp_expr):
        self._validate_expr(comp_expr.lh_expr)
        self._validate_expr(comp_expr.rh_expr)

    def _validate_expr(self, expr):
        if type(expr) in self._validate_expr_cbs:
            self._validate_expr_cbs[type(expr)](expr)


class _MatchContext:
    def __init__(self, evt, begin_evt, parent_begin_evt):
        self._evt = evt
        self._begin_evt = begin_evt
        self._parent_begin_evt = parent_begin_evt

    @property
    def evt(self):
        return self._evt

    @property
    def begin_evt(self):
        return self._begin_evt

    @property
    def parent_begin_evt(self):
        return self._parent_begin_evt


_DYN_SCOPE_TO_BT_CTF_SCOPE = {
    DynScope.TPH: bt.CTFScope.TRACE_PACKET_HEADER,
    DynScope.SPC: bt.CTFScope.STREAM_PACKET_CONTEXT,
    DynScope.SEH: bt.CTFScope.STREAM_EVENT_HEADER,
    DynScope.SEC: bt.CTFScope.STREAM_EVENT_CONTEXT,
    DynScope.EC: bt.CTFScope.EVENT_CONTEXT,
    DynScope.EP: bt.CTFScope.EVENT_FIELDS,
}


def _resolve_event_expr(event, expr):
    # event not found
    if event is None:
        return

    # event name
    if type(expr.child) is EventName:
        return event.name

    # default, automatic dynamic scope
    dyn_scope = DynScope.AUTO

    if type(expr.child) is DynamicScope:
        # select specific dynamic scope
        expr = expr.child
        dyn_scope = expr.dyn_scope

    if type(expr.child) is EventFieldName:
        expr = expr.child

        if dyn_scope == DynScope.AUTO:
            # automatic dynamic scope
            if expr.name in event:
                return event[expr.name]

            # event field not found
            return

        # specific dynamic scope
        bt_ctf_scope = _DYN_SCOPE_TO_BT_CTF_SCOPE[dyn_scope]

        return event.field_with_scope(expr.name, bt_ctf_scope)

    assert(False)

# This exquisite function takes an expression and resolves it to
# an actual value (Python's number/string) considering the current
# matching context.
def _resolve_expr(expr, match_context):
    if type(expr) is ParentScope:
        begin_scope = expr.child
        event_scope = begin_scope.child

        return _resolve_event_expr(match_context.parent_begin_evt, event_scope)

    if type(expr) is BeginScope:
        # event in the begin context
        event_scope = expr.child

        return _resolve_event_expr(match_context.begin_evt, event_scope)

    if type(expr) is EventScope:
        # current event
        return _resolve_event_expr(match_context.evt, expr)

    if type(expr) is Number:
        return expr.value

    if type(expr) is String:
        return expr.value

    assert(False)


class _Matcher:
    def __init__(self, expr, match_context):
        self._match_context = match_context
        self._expr_matchers = {
            LogicalAnd: self._and_expr_matches,
            LogicalNot: self._not_expr_matches,
            Eq: partial(self._comp_expr_matches, lambda lh, rh: lh == rh),
            Lt: partial(self._comp_expr_matches, lambda lh, rh: lh < rh),
            LtEq: partial(self._comp_expr_matches, lambda lh, rh: lh <= rh),
            Gt: partial(self._comp_expr_matches, lambda lh, rh: lh > rh),
            GtEq: partial(self._comp_expr_matches, lambda lh, rh: lh >= rh),
        }
        self._matches = self._expr_matches(expr)

    def _and_expr_matches(self, expr):
        return (self._expr_matches(expr.lh_expr) and
                self._expr_matches(expr.rh_expr))

    def _not_expr_matches(self, expr):
        return not self._expr_matches(expr.expr)

    def _comp_expr_matches(self, compfn, expr):
        lh_value = _resolve_expr(expr.lh_expr, self._match_context)
        rh_value = _resolve_expr(expr.rh_expr, self._match_context)

        # make sure both sides are found
        if lh_value is None or rh_value is None:
            return False

        # cast RHS to int if LHS is an int
        if type(lh_value) is int and type(rh_value) is float:
            rh_value = int(rh_value)

        # compare types first
        if type(lh_value) is not type(rh_value):
            return False

        # compare field to a literal value
        return compfn(lh_value, rh_value)

    def _expr_matches(self, expr):
        return self._expr_matchers[type(expr)](expr)

    @property
    def matches(self):
        return self._matches


def _expr_matches(expr, match_context):
    return _Matcher(expr, match_context).matches


def create_conjunction_from_exprs(exprs):
    if len(exprs) == 0:
        return

    cur_expr = exprs[0]

    for expr in exprs[1:]:
        cur_expr = LogicalAnd(cur_expr, expr)

    return cur_expr


@enum.unique
class PeriodEngineCallbackType(enum.Enum):
    PERIOD_BEGIN = 1
    PERIOD_END = 2


class Period:
    def __init__(self, definition, parent, begin_evt, begin_captures):
        begin_evt_copy = core_event.Event(begin_evt)
        self._begin_evt = begin_evt_copy
        self._end_evt = None
        self._completed = False
        self._definition = definition
        self._parent = parent
        self._children = set()
        self._begin_captures = begin_captures
        self._end_captures = {}

    @property
    def begin_evt(self):
        return self._begin_evt

    @property
    def end_evt(self):
        return self._end_evt

    @end_evt.setter
    def end_evt(self, evt):
        self._end_evt = evt

    @property
    def definition(self):
        return self._definition

    @property
    def parent(self):
        return self._parent

    @property
    def children(self):
        return self._children

    @property
    def completed(self):
        return self._completed

    @completed.setter
    def completed(self, value):
        self._completed = value

    @property
    def begin_captures(self):
        return self._begin_captures

    @property
    def end_captures(self):
        return self._end_captures


class PeriodEngine:
    def __init__(self,  registry, cbs):
        self._registry = registry
        self._cbs = cbs
        self._root_periods = set()

    def _cb_period_end(self, period):
        self._cbs[PeriodEngineCallbackType.PERIOD_END](period)

    def _cb_period_begin(self, period):
        self._cbs[PeriodEngineCallbackType.PERIOD_BEGIN](period)

    def _create_period(self, definition, parent, begin_evt, begin_captures):
        return Period(definition, parent, begin_evt, begin_captures)

    def _get_captures(self, captures_exprs, match_context):
        captures = {}

        for name, capture_expr in captures_exprs.items():
            captures[name] = _resolve_expr(capture_expr, match_context)

        return captures

    def _process_event_add_periods(self, parent_period,
                                   child_periods, child_period_defs, evt):
        periods_to_add = set()

        for child_period_def in child_period_defs:
            match_context = _MatchContext(evt, evt, None)

            if _expr_matches(child_period_def.begin_expr, match_context):
                # match! add period
                captures = self._get_captures(
                    child_period_def.begin_captures_exprs,
                    match_context)
                period = self._create_period(child_period_def,
                                             parent_period, evt, captures)
                periods_to_add.add(period)

        # safe to add child periods now, outside the iteration
        for period_to_add in periods_to_add:
            self._cb_period_begin(period_to_add)
            child_periods.add(period_to_add)

        for child_period in child_periods:
            self._process_event_add_periods(child_period,
                                            child_period.children,
                                            child_period.definition.children,
                                            evt)

    def _process_event_begin(self, evt):
        defs = self._registry.root_period_defs
        self._process_event_add_periods(None, self._root_periods, defs, evt)

    def _create_end_match_context(self, period, evt):
        parent_begin_evt = None

        if period.parent is not None:
            parent_begin_evt = period.parent.begin_evt

        return _MatchContext(evt, period.begin_evt, parent_begin_evt)

    def _process_event_remove_period(self, child_periods, evt):
        for child_period in child_periods:
            self._process_event_remove_period(child_period.children, evt)

        child_periods_to_remove = set()

        for child_period in child_periods:
            match_context = self._create_end_match_context(child_period, evt)

            if _expr_matches(child_period.definition.end_expr, match_context):
                # set period's end captures
                end_captures_exprs = child_period.definition.end_captures_exprs
                captures = self._get_captures(end_captures_exprs, match_context)
                child_period._end_captures = captures

                # mark as to be removed
                child_periods_to_remove.add(child_period)

        # safe to remove child periods now, outside the iteration
        for child_period_to_remove in child_periods_to_remove:
            # set period's ending event and completed property
            child_period_to_remove.end_evt = evt
            child_period_to_remove.completed = True

            # also remove its own remaining child periods
            self._remove_periods(child_period_to_remove.children, evt)

            # call end of period user callback (this period matched)
            self._cb_period_end(child_period_to_remove)

            # remove period from set
            child_periods.remove(child_period_to_remove)

    def _process_event_end(self, evt):
        self._process_event_remove_period(self._root_periods, evt)

    def process_event(self, evt):
        self._process_event_end(evt)
        self._process_event_begin(evt)

    def _remove_periods(self, child_periods, evt):
        for child_period in child_periods:
            self._remove_periods(child_period.children, evt)

        # safe to remove child periods now, outside the iteration
        for child_period in child_periods:
            # set period's ending event and completed property
            child_period.end_evt = evt
            child_period.completed = False

            # call end of period user callback
            self._cb_period_end(child_period)

        child_periods.clear()

    def remove_all_periods(self):
        self._remove_periods(self._root_periods, None)

    @property
    def root_periods(self):
        return self._root_periods
