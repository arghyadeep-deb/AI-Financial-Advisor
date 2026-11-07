"""Synthetic v1 goldens: expected values are hand calculated in comments."""
from datetime import date
from dataclasses import replace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.finance.allocation_sources import synthetic_fixture, production_registry
from backend.finance.suitability import Suitability
from backend.knowledge.registry import Registry
from backend.models.models import FinancialProfile, User
from backend.services.allocation_service import create_scenario, read_plan, propose
from backend.services.output_guard import guard_allocation
from engines.allocation import allocate
from engines.allocation.contracts import Constraints, Holding
from engines.allocation.costs import compare, stress
from engines.cashflow import build_snapshot

DAY = date(2026, 11, 7)


def answers(**changes):
    return Suitability(**{**dict(revision=1, horizon_months=120, essential_goals_declared=False,
                                dependants=0, income_stable=True, debt_reviewed=True, reserves_reviewed=True,
                                experience="some", loss_tolerance="high", loss_capacity="high"), **changes})


def snapshot(**changes):
    return build_snapshot({**dict(income_paise=1000000, expenses_paise=500000,
                                  savings_paise=3000000, debt_balance_paise=0), **changes},
                          owner_id=1, profile_revision=1)


def run(*, snap=None, suitability=None, constraints=None, registry=None, day=DAY, pack=None):
    p, r = synthetic_fixture()
    return allocate(snap or snapshot(), suitability or answers(), pack or p,
                    constraints or Constraints(eligible_liquid_paise=1000000),
                    registry if registry is not None else r, owner_id=1, as_of=day)


def test_independent_cash_cost_stress_goldens():
    # 1,000,000 - 500,000 = 500,000; fully funded reserve; 90% = 450,000.
    # 20/30/50% = 90,000 / 135,000 / 225,000 paise. Fees 1,350+4,500=5,850.
    plan = run()
    assert plan.status == "feasible"
    assert [h.value_paise for h in plan.amounts] == [90000, 135000, 225000]
    assert plan == run()
    pack, _ = synthetic_fixture()
    c = compare(plan, (Holding(asset="equity", value_paise=100000),), pack, sale_paise=50000)
    assert c["contribution_first"]["annual_fee_estimate_paise"] == 5850
    assert c["contribution_first"]["sales_paise"] == 0
    assert c["tax_cost_paise"] is None and c["net_improvement"] is None
    assert c["cost_basis_status"] == "unknown"
    # Downside 90,000+121,500+135,000; upside 90,000+141,750+270,000.
    assert stress(plan, pack)["adverse_terminal_paise"] == 346500
    assert stress(plan, pack)["favourable_terminal_paise"] == 501750


@pytest.mark.parametrize("changes", [dict(horizon_months=None), dict(essential_goals_declared=True, essential_goal_months=12),
                                     dict(loss_capacity="low"), dict(income_stable=False), dict(dependants=None)])
def test_suitability_conflicts(changes):
    p = run(suitability=answers(**changes))
    assert p.status == "insufficient_data" and p.reasons


def test_low_capacity_and_short_horizon_constrain_equity():
    plan = run(suitability=answers(loss_tolerance="low", loss_capacity="low", horizon_months=12))
    assert plan.status == "feasible"
    assert plan.amounts[2].value_paise == 0


@pytest.mark.parametrize("snap,status", [(snapshot(income_paise=4500000, expenses_paise=5500000), "infeasible"),
                                        (snapshot(debt_balance_paise=100, monthly_debt_payment_paise=None), "insufficient_data"),
                                        (snapshot(income_paise=500000), "infeasible")])
def test_zero_deficit_unknown_refuse(snap, status):
    assert run(snap=snap).status == status


def test_liquidity_exclusions_integer_rounding():
    assert run(constraints=Constraints()).status == "insufficient_data"
    assert run(constraints=Constraints(eligible_liquid_paise=0)).status == "infeasible"
    assert run(constraints=Constraints(eligible_liquid_paise=1)).status == "feasible"
    assert run(constraints=Constraints(eligible_liquid_paise=10, excluded=("cash",))).status == "infeasible"
    plan = run(constraints=Constraints(eligible_liquid_paise=101, excluded=("equity",)))
    assert [h.value_paise for h in plan.amounts] == [71, 30, 0]
    assert sum(h.value_paise for h in plan.amounts) == 101
    pack, _ = synthetic_fixture()
    tight = tuple(b.model_copy(update={"minimum_bps": 5000, "target_bps": 5000}) for b in pack.assets)
    assert run(constraints=Constraints(eligible_liquid_paise=100, bounds=tight)).status == "infeasible"


def test_expiry_correction_unapproved_and_tamper():
    pack, registry = synthetic_fixture()
    assert run(day=date(2027, 1, 1)).status == "insufficient_data"
    assert run(registry=production_registry()).status == "insufficient_data"
    source = registry.retrieve("allocation", owner_id=1, as_of=DAY)[0]
    corrected = source.model_copy(update={"version": 2, "approved": False})
    assert run(registry=Registry((source, corrected), frozenset({"example.test"}))).status == "insufficient_data"
    assert run(pack=pack.model_copy(update={"version": "tampered"})).status == "insufficient_data"
    private = source.model_copy(update={"owner_id": 2})
    assert run(registry=Registry((private,), frozenset({"example.test"}))).status == "insufficient_data"


def test_invalid_contracts_and_wrong_snapshot_owner():
    for amount in (-1, True, 1.1, 10**14):
        with pytest.raises(ValidationError):
            Constraints(eligible_liquid_paise=amount)
    with pytest.raises(ValueError, match="owner"):
        run(snap=replace(snapshot(), owner_id=2))


def test_guard_gate_and_no_http_surface(monkeypatch):
    monkeypatch.setenv("NAMED_PRODUCT_RECOMMENDATIONS", "true")
    malicious = {"amounts": [999999999], "product": "Named Fund", "public_eligible": True}
    canonical = {"allocation": run().model_dump(mode="json")}
    safe = guard_allocation(canonical, malicious)
    assert safe["allocation"] == canonical["allocation"]
    assert safe["public_eligible"] is False and safe["named_products_eligible"] is False
    assert "product" not in safe and propose(**malicious)["status"] == "gated"
    from backend.main import app
    assert not any("allocation" in route.path for route in app.routes)


def seed(db):
    db.add_all([User(id=1, email="a@synthetic.test", full_name="A", hashed_password="disabled"),
                User(id=2, email="b@synthetic.test", full_name="B", hashed_password="disabled")])
    db.flush()
    db.add(FinancialProfile(user_id=1, revision=1, monthly_income_paise=1000000,
                           monthly_expenses_paise=500000, existing_savings_paise=3000000,
                           existing_investments_paise=0, existing_debts_paise=0,
                           monthly_credit_spend_paise=0))
    db.commit()


def test_owned_immutable_stale_history(db_engine):
    pack, registry = synthetic_fixture()
    with Session(db_engine) as db:
        seed(db)
        p = create_scenario(db, owner_id=1, expected_revision=1, suitability=answers(), pack=pack,
                            constraints=Constraints(eligible_liquid_paise=1000000), registry=registry, as_of=DAY)
        args = dict(owner_id=1, plan_id=p["id"], registry=registry, as_of=DAY,
                    suitability_revision=1, assumption_version=pack.version)
        assert not read_plan(db, **args)["stale"]
        for uid, pid in [(2, p["id"]), (2, "missing")]:
            with pytest.raises(HTTPException) as e:
                read_plan(db, **{**args, "owner_id": uid, "plan_id": pid})
            assert (e.value.status_code, e.value.detail) == (404, "Allocation plan not found")
        with pytest.raises(Exception, match="immutable"):
            db.execute(text("UPDATE allocation_plans SET suitability_revision=2"))
        db.rollback()
        assert read_plan(db, **{**args, "suitability_revision": 2})["stale"]
        assert read_plan(db, **{**args, "as_of": date(2027, 1, 1)})["stale"]
        assert read_plan(db, **{**args, "holdings_revision": "changed"})["stale"]
        db.query(FinancialProfile).filter_by(user_id=1).update({"revision": 2})
        db.commit()
        assert read_plan(db, **args)["stale"]
        with pytest.raises(HTTPException) as e:
            create_scenario(db, owner_id=1, expected_revision=1, suitability=answers(), pack=pack,
                            constraints=Constraints(), registry=registry, as_of=DAY)
        assert e.value.status_code == 409
