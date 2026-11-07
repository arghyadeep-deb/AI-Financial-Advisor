from dataclasses import replace

import pytest

from backend.finance.allocation_sources import synthetic_fixture
from engines.allocation import allocate
from engines.allocation.contracts import Constraints
from tests.allocation.test_allocation import DAY, answers, snapshot


def run(*, budget=10000, suitability=None, constraints=None, snap=None):
    pack, registry = synthetic_fixture('v2')
    return allocate(snap or snapshot(), suitability or answers(), pack,
        constraints or Constraints(eligible_liquid_paise=budget), registry, owner_id=1, as_of=DAY, synthetic_test=True)


def test_four_class_independent_golden():
    result = run()
    assert result.status == 'feasible'
    assert {h.asset: h.value_paise for h in result.amounts} == dict(cash=2000, debt=3000, equity=4000, gold=1000)
    assert result == run()
    assert result.rule_version == 'allocation.v2'


@pytest.mark.parametrize('budget', [1, 2, 3, 7, 11, 101, 9999, 10001, 450001])
@pytest.mark.parametrize('excluded', [(), ('equity',), ('gold',), ('debt', 'equity', 'gold')])
def test_integer_cash_conservation_and_sourced_bounds(budget, excluded):
    result = run(constraints=Constraints(eligible_liquid_paise=budget, excluded=excluded))
    assert result.status == 'feasible'
    pack, _ = synthetic_fixture('v2')
    actual = {h.asset: h.value_paise for h in result.amounts}
    expected_budget = min(450000, budget)
    assert sum(actual.values()) == expected_budget
    for b in pack.assets:
        assert actual[b.asset] >= (expected_budget*b.minimum_bps+9999)//10000
        assert actual[b.asset] <= expected_budget*b.maximum_bps//10000
        if b.asset in excluded:
            assert actual[b.asset] == 0
    assert result == run(constraints=Constraints(eligible_liquid_paise=budget, excluded=excluded))


def test_tolerance_and_near_term_risk_limits():
    result = run(suitability=answers(loss_tolerance='low'))
    amounts = {h.asset: h.value_paise for h in result.amounts}
    assert amounts['equity'] <= 1000 and amounts['gold'] == 0
    result = run(suitability=answers(loss_tolerance='low', horizon_months=12))
    amounts = {h.asset: h.value_paise for h in result.amounts}
    assert amounts['equity'] == amounts['gold'] == 0
    liquid = run(constraints=Constraints(eligible_liquid_paise=10000, maximum_liquidity_days=0))
    assert liquid.status == 'infeasible' and not liquid.amounts
    assert all(n is None for n in liquid.liquidity_days.values())


def test_impossible_bounds_deficit_missing_and_wrong_owner():
    pack, _ = synthetic_fixture('v2')
    impossible = tuple(b.model_copy(update={'minimum_bps': 3000, 'target_bps': 3000, 'maximum_bps': 3000}) for b in pack.assets)
    for constraints in (Constraints(eligible_liquid_paise=100, bounds=impossible),
                        Constraints(eligible_liquid_paise=100, bounds=()),
                        Constraints(eligible_liquid_paise=100, excluded=('cash',)),
                        Constraints(eligible_liquid_paise=100, liquidity_floor_bps=10000, excluded=('cash',))):
        result = run(constraints=constraints)
        assert result.status == 'infeasible' and not result.amounts and result.reasons
    assert run(snap=snapshot(income_paise=4500000, expenses_paise=5500000)).status == 'infeasible'
    assert run(constraints=Constraints()).status == 'insufficient_data'
    with pytest.raises(ValueError, match='owner'):
        run(snap=replace(snapshot(), owner_id=2))
