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

import pyparsing as pp
from ..core import period


class MalformedExpression(Exception):
    pass


class PeriodExists(Exception):
    pass


class NoSuchParent(Exception):
    pass


# basic expression grammar
_e = pp.CaselessLiteral('e')
_number = pp.Combine(pp.Word('+-' + pp.nums, pp.nums) +
                     pp.Optional('.' + pp.Optional(pp.Word(pp.nums))) +
                     pp.Optional(_e + pp.Word('+-' + pp.nums,
                                 pp.nums))).setResultsName('number')
_quoted_string = pp.QuotedString('"', '\\').setResultsName('quoted-string')
_identifier = pp.Word(pp.alphas + '_', pp.alphanums + '_').setResultsName('id')
_tph_scope_prefix = pp.Literal(period.DynScope.TPH.value).setResultsName(
    'tph-scope-prefix')
_spc_scope_prefix = pp.Literal(period.DynScope.SPC.value).setResultsName(
    'spc-scope-prefix')
_seh_scope_prefix = pp.Literal(period.DynScope.SEH.value).setResultsName(
    'seh-scope-prefix')
_sec_scope_prefix = pp.Literal(period.DynScope.SEC.value).setResultsName(
    'sec-scope-prefix')
_ec_scope_prefix = pp.Literal(period.DynScope.EC.value).setResultsName(
    'ec-scope-prefix')
_ep_scope_prefix = pp.Literal(period.DynScope.EP.value).setResultsName(
    'ep-scope-prefix')
_dyn_scope_prefix = pp.Group(pp.Group(_tph_scope_prefix |
                                      _spc_scope_prefix |
                                      _seh_scope_prefix |
                                      _sec_scope_prefix |
                                      _ec_scope_prefix |
                                      _ep_scope_prefix) +
                             '.').setResultsName('dyn-scope-prefix')
_parent_scope_prefix = pp.Group(pp.Literal('$parent') + '.').setResultsName(
    'parent-scope-prefix')
_begin_scope_prefix = pp.Group(pp.Literal('$begin') + '.').setResultsName(
    'begin-scope-prefix')
_event_scope_prefix = pp.Group(pp.Literal('$evt') + '.').setResultsName(
    'event-scope-prefix')
_event_field = pp.Group(pp.Optional(_parent_scope_prefix) +
                        pp.Optional(_begin_scope_prefix) +
                        _event_scope_prefix +
                        pp.Optional(_dyn_scope_prefix) +
                        _identifier).setResultsName('event-field')
_event_name = pp.Group(pp.Optional(_parent_scope_prefix) +
                       pp.Optional(_begin_scope_prefix) +
                       _event_scope_prefix +
                       '$name').setResultsName('event-name')
_relop = pp.Group(pp.Literal('==') | '!=' | '<=' | '>=' | '<' |
                  '>').setResultsName('relop')
_eqop = pp.Group(pp.Literal('==') | '!=').setResultsName('eqop')
_name_comp_expr = pp.Group(_event_name + _eqop +
                           _quoted_string).setResultsName('name-comp-expr')
_number_comp_expr = pp.Group(_event_field + _relop +
                             _number).setResultsName('number-comp-expr')
_string_comp_expr = pp.Group(_event_field + _eqop +
                             _quoted_string).setResultsName('string-comp-expr')
_field_comp_expr = pp.Group(_event_field.setResultsName('lh') + _relop +
                            _event_field.setResultsName('rh')).setResultsName(
                                    'field-comp-expr')
_conj_exprs = pp.delimitedList(_name_comp_expr |
                               _number_comp_expr |
                               _string_comp_expr |
                               _field_comp_expr, '&&')
_parent_name = pp.Literal('(') + _identifier + ')'
_period_info = pp.Group(_identifier.setResultsName('name') +
                        pp.Optional(_parent_name).setResultsName(
                            'parent-name')).setResultsName('period-info')
_period = pp.Optional(_period_info) + ':' + \
          _conj_exprs.setResultsName('begin-expr') + \
          pp.Optional(pp.Literal(':') + _conj_exprs.setResultsName('end-expr'))


# relational operator string -> function which creates an expression
_RELOP_TO_EXPR = {
    '==': lambda lh, rh: period.Eq(lh, rh),
    '!=': lambda lh, rh: period.LogicalNot(period.Eq(lh, rh)),
    '<': lambda lh, rh: period.Lt(lh, rh),
    '<=': lambda lh, rh: period.LtEq(lh, rh),
    '>': lambda lh, rh: period.Gt(lh, rh),
    '>=': lambda lh, rh: period.GtEq(lh, rh),
}


def _res_to_scope(res):
    if res[-1] == '$name':
        scope = period.EventName()
    elif 'id' in res:
        scope = period.EventFieldName(res['id'])
    else:
        assert(False)

    if 'dyn-scope-prefix' in res:
        dyn_scope = period.DynScope(res['dyn-scope-prefix'][0][0])
        scope = period.DynamicScope(dyn_scope, scope)

    scope = period.EventScope(scope)

    if 'begin-scope-prefix' in res:
        scope = period.BeginScope(scope)

    if 'parent-scope-prefix' in res:
        scope = period.ParentScope(scope)

    return scope


def _res_quoted_string_to_string_expression(res_quoted_string):
    return period.String(str(res_quoted_string))


def _res_number_to_number_expression(res_number):
    return period.Number(float(str(res_number)))


def _create_binary_op(relop, lh, rh):
    return _RELOP_TO_EXPR[relop[0]](lh, rh)


def _parse_results_to_expression(res_conj_exprs):
    exprs = []

    for res_expr in res_conj_exprs:
        res_expr_name = res_expr.getName()

        if res_expr_name == 'name-comp-expr':
            ev_name_expr = _res_to_scope(res_expr['event-name'])
            str_expr = _res_quoted_string_to_string_expression(
                res_expr['quoted-string'])
            expr = _create_binary_op(res_expr['eqop'], ev_name_expr, str_expr)
        elif res_expr_name == 'number-comp-expr':
            field_expr = _res_to_scope(res_expr['event-field'])
            number_expr = _res_number_to_number_expression(res_expr['number'])
            expr = _create_binary_op(res_expr['relop'], field_expr,
                                     number_expr)
        elif res_expr_name == 'string-comp-expr':
            field_expr = _res_to_scope(res_expr['event-field'])
            str_expr = _res_quoted_string_to_string_expression(
                res_expr['quoted-string'])
            expr = _create_binary_op(res_expr['eqop'], field_expr, str_expr)
        elif res_expr_name == 'field-comp-expr':
            lh_field_expr = _res_to_scope(res_expr['lh'])
            rh_field_expr = _res_to_scope(res_expr['rh'])
            expr = _create_binary_op(res_expr['relop'], lh_field_expr,
                                     rh_field_expr)
        else:
            assert(False)

        exprs.append(expr)

    return period.create_conjunction_from_exprs(exprs)


class PeriodArgParseResults:
    def __init__(self, parent_name, period_name, begin_expr, end_expr):
        self._parent_name = parent_name
        self._period_name = period_name
        self._begin_expr = begin_expr
        self._end_expr = end_expr

    @property
    def parent_name(self):
        return self._parent_name

    @property
    def period_name(self):
        return self._period_name

    @property
    def begin_expr(self):
        return self._begin_expr

    @property
    def end_expr(self):
        return self._end_expr


def parse_period_arg(arg):
    try:
        period_res = _period.parseString(arg, parseAll=True)
    except Exception:
        raise MalformedExpression(arg)

    period_name = None
    parent_name = None

    if 'period-info' in period_res:
        period_info_res = period_res['period-info']
        period_name = period_info_res['name']

        if 'parent-name' in period_info_res:
            parent_name = period_info_res['parent-name']['id']

    begin_expr = _parse_results_to_expression(period_res['begin-expr'])

    if 'end-expr' in period_res:
        end_expr = _parse_results_to_expression(period_res['end-expr'])
    else:
        end_expr = begin_expr

    return PeriodArgParseResults(parent_name, period_name, begin_expr,
                                 end_expr)
