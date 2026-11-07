"""Bounded evidence-only return contracts; no inferred flows or market data."""
from datetime import date
from decimal import Decimal, localcontext
from fractions import Fraction
from backend.core.money import check_paise


def xirr(flows: tuple[tuple[date, int], ...], *, corporate_actions_supported: bool) -> dict:
    """ACT/365 annual return, conventional one-outflow schedule only.

    Nonconventional signs can have multiple roots and are refused. Terminal
    value must be supplied as a dated final inflow; this function never invents it.
    Bisection domain (-0.9999,1000), tolerance 1e-20, at most 180 iterations.
    """
    unavailable = {'status': 'unavailable', 'annual_rate': None, 'method': 'ACT/365 conventional XIRR.v1'}
    if not corporate_actions_supported:
        return {**unavailable, 'reason': 'corporate_actions_unsupported'}
    if not 2 <= len(flows) <= 256:
        return {**unavailable, 'reason': 'dated_flows_required'}
    for day, amount in flows:
        if type(day) is not date:
            raise ValueError('Exact flow date required')
        check_paise(amount)
    if list(flows) != sorted(flows) or len({d for d, _ in flows}) != len(flows):
        return {**unavailable, 'reason': 'distinct_ordered_dates_required'}
    if flows[0][1] >= 0 or any(n <= 0 for _, n in flows[1:]):
        return {**unavailable, 'reason': 'no_solution_or_multiple_roots_unsupported'}
    with localcontext() as ctx:
        ctx.prec = 50
        times = [Decimal((d-flows[0][0]).days) / 365 for d, _ in flows]
        def npv(rate):
            return sum(Decimal(n) / (1+rate)**t for (_, n), t in zip(flows, times))
        low, high = Decimal('-0.9999'), Decimal('1000')
        if npv(low) < 0 or npv(high) > 0:
            return {**unavailable, 'reason': 'no_root_in_supported_domain'}
        for _ in range(180):
            mid = (low+high)/2
            if npv(mid) > 0:
                low = mid
            else:
                high = mid
            if high-low < Decimal('1e-20'):
                return {'status': 'calculated', 'annual_rate': str(mid.quantize(Decimal('0.000000000001'))),
                        'method': unavailable['method'], 'currency': 'INR', 'terminal_value': 'explicit_final_inflow'}
    return {**unavailable, 'reason': 'no_convergence'}


def time_weighted(intervals: tuple[tuple[int, int, int], ...], *, evidence_complete: bool) -> dict:
    """Explicit end-of-interval external flows: (close-flow)/open per interval."""
    if not evidence_complete or not intervals:
        return {'status': 'unavailable', 'return_fraction': None}
    product = Fraction(1)
    for opening, closing, end_flow in intervals:
        for value in (opening, closing, end_flow):
            check_paise(value)
        if opening <= 0 or closing < 0 or closing-end_flow < 0:
            return {'status': 'unavailable', 'return_fraction': None}
        product *= Fraction(closing-end_flow, opening)
    return {'status': 'calculated', 'return_fraction': str(product-1),
            'method': 'end-flow time-weighted.v1', 'currency': 'INR'}
