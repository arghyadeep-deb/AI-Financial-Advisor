from uuid import uuid4

from sqlalchemy.orm import Session

from backend.models.models import AllocationPlan, PortfolioRevision
from backend.services import allocation_service as allocation, portfolio_service as portfolio
from tests.test_stage_e import DAY, save_inputs, scenario


def test_legacy_request_defaults_replay_original_immutable_result(db_engine, monkeypatch):
    monkeypatch.setenv('ALLOCATION_SANDBOX_ENABLED', 'true')
    monkeypatch.setattr(portfolio, 'today', lambda: DAY)
    with Session(db_engine) as db:
        save_inputs(db)
        first = allocation.create_owned_scenario(db, 1, scenario())
        legacy_request = scenario()
        inputs = {**first['inputs'], 'request': legacy_request.model_dump(mode='json')}
        for added in ('excluded_assets', 'liquidity_floor_bps', 'maximum_liquidity_days'):
            inputs['request'].pop(added)
        result = db.get(AllocationPlan, first['id']).result
        legacy_id = uuid4().hex
        db.add(AllocationPlan(id=legacy_id, user_id=1, profile_revision=1, suitability_revision=1,
                              input_snapshot=inputs, result=result))
        db.commit()
        replay = allocation.create_owned_scenario(db, 1, legacy_request)
        assert replay['id'] == legacy_id and replay['allocation'] == first['allocation']
        assert 'excluded_assets' not in db.get(AllocationPlan, legacy_id).input_snapshot['request']
        saved = db.query(PortfolioRevision).filter_by(user_id=1, kind='suitability').one()
        assert saved.request['suitability_assessment']['assessment_rule_version'] == 'suitability-assessment.v1'
