import pytest

from backend.finance.allocation_sources import synthetic_fixture
from engines.allocation.contracts import Holding
from engines.allocation.costs import compare, rebalance
from tests.allocation.test_stage_i_solver import run


@pytest.mark.parametrize('basis', [None, 0, 9000, 15000])
def test_unknown_tax_even_with_basis_never_claims_saving(basis):
    pack, _ = synthetic_fixture('v2')
    result = compare(run(), (Holding(asset='equity', value_paise=20000),), pack,
                     sale_paise=10000, cost_basis_paise=basis)
    assert result['tax_cost_paise'] is result['net_improvement'] is None
    assert result['exit_load_paise'] is result['transaction_cost_paise'] is None
    assert result['net_improvement_status'] == 'blocked_unknown_costs'
    assert result['contribution_first']['sales_paise'] == 0
    # 3000*1% + 4000*2% + 1000*1.5% = 125 paise per year.
    assert result['contribution_first']['annual_fee_estimate_paise'] == 125
    assert result['contribution_first']['resulting_holdings_paise'] == dict(cash=2000, debt=3000, equity=24000, gold=1000)
    assert result['baseline']['new_cash_paise'] == 10000
    assert result['baseline']['existing_holdings_paise'] == {'equity': 20000}


def test_four_class_contribution_first_independent_golden():
    holdings = (Holding(asset='equity', value_paise=80000), Holding(asset='cash', value_paise=20000))
    result = rebalance(holdings, 10000, dict(cash=2000, debt=3000, equity=4000, gold=1000))
    # 110,000 combined target: 22,000 / 33,000 / 44,000 / 11,000.
    assert result['target_paise'] == dict(cash=22000, debt=33000, equity=44000, gold=11000)
    assert result['contribution_first']['additions_paise'] == dict(cash=2000, debt=8000, equity=0, gold=0)
    assert result['contribution_first']['result_paise'] == dict(cash=22000, debt=8000, equity=80000, gold=0)
    assert result['sale_alternative']['sales_paise'] == 36000
    assert sum(result['sale_alternative']['delta_paise'].values()) == 10000
    assert result['tax_cost_paise'] is result['net_improvement'] is None
    assert not result['execution_enabled']


def test_gold_is_never_silently_dropped_and_inputs_are_bounded():
    gold = (Holding(asset='gold', value_paise=100),)
    with pytest.raises(ValueError, match='universe'):
        rebalance(gold, 0, dict(cash=2000, debt=3000, equity=5000))
    result = rebalance(gold, 1, dict(cash=2000, debt=3000, equity=4000, gold=1000))
    assert sum(result['contribution_first']['result_paise'].values()) == 101
    assert sum(result['target_paise'].values()) == 101
    pack, _ = synthetic_fixture('v2')
    with pytest.raises(ValueError, match='Sale exceeds'):
        compare(run(), gold, pack, sale_paise=101)
    with pytest.raises(ValueError, match='assumptions'):
        compare(run(), gold, pack.model_copy(update={'version': 'changed'}))
    with pytest.raises(ValueError):
        rebalance((Holding(asset='gold', value_paise=10**13),), 1, dict(cash=10000, debt=0, equity=0, gold=0))
