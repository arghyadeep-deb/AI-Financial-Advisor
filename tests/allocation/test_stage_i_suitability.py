"""Suitability contract acceptance, synthetic answers only."""
import pytest
from pydantic import ValidationError

from backend.finance.suitability import Suitability


def complete(**changes):
    return Suitability(**{**dict(revision=1, horizon_months=120,
        essential_goals_declared=False, dependants=0, income_stable=True,
        debt_reviewed=True, reserves_reviewed=True, experience='some',
        loss_tolerance='high', loss_capacity='high'), **changes})


@pytest.mark.parametrize('field', ['horizon_months', 'essential_goals_declared', 'dependants',
    'income_stable', 'debt_reviewed', 'reserves_reviewed', 'experience', 'loss_tolerance', 'loss_capacity'])
def test_each_material_missing_answer_blocks(field):
    report = complete(**{field: None}).assessment()
    assert report['blocks_personalized_proposal']
    assert f'Provide {field}' in report['reasons']
    assert report['resolution'] and not report['public_eligible']


@pytest.mark.parametrize('changes,reason', [
    ({'loss_capacity': 'low'}, 'Resolve tolerance exceeding loss capacity'),
    ({'essential_goals_declared': True, 'essential_goal_months': 12},
     'Resolve high tolerance against near-term needs or unstable income'),
    ({'income_stable': False}, 'Resolve high tolerance against near-term needs or unstable income'),
    ({'essential_goal_months': 12}, 'Resolve contradictory essential goal answers'),
    ({'reserves_reviewed': False}, 'Review debt and reserve needs'),
    ({'essential_goals_declared': True}, 'Provide essential goal horizon'),
])
def test_contradictions_are_reviewable_not_silently_resolved(changes, reason):
    original = complete(**changes)
    assert reason in original.assessment()['reasons']
    assert original.model_dump() == complete(**changes).model_dump()


def test_complete_record_still_has_no_public_permission():
    report = complete().assessment()
    assert report['status'] == 'complete' and not report['blocks_personalized_proposal']
    assert report['capacity_basis'] == 'owner_declared_unverified' and not report['public_eligible']
    with pytest.raises(ValidationError):
        Suitability(revision=1, age=30)
    with pytest.raises(ValidationError):
        complete(horizon_months=True)
