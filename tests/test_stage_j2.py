import pytest
from sqlalchemy.orm import Session
from fastapi import HTTPException
from tests.test_stage_j import households, sharing, book, observation, permission
from backend.services import household_service as service


def test_resource_permission_isolation(db_engine):
    with Session(db_engine) as db:
        a, b, c, house, _, _ = sharing(db)
        service.write(db, a.id, 'networth', book([observation(), observation('secret')]))
        grant = permission(b.id).model_copy(update={'permissions': {'summaries'}})
        service.grant(db, a.id, house['id'], grant)
        result = service.shared_view(db, b.id, house['id'], a.id, 'networth', resource='property')
        assert [x['reference'] for x in result['data']['observations']] == ['property']
        for resource in ('secret', 'missing', None):
            with pytest.raises(HTTPException) as exc:
                service.shared_view(db, b.id, house['id'], a.id, 'networth', resource=resource)
            assert exc.value.status_code == 404
        with pytest.raises(HTTPException):
            service.request_export(db, b.id, house['id'], a.id, 'networth', resource='property')
        service.grant(db, a.id, house['id'], grant.model_copy(update={'expected_revision': 1, 'permissions': {'exports'}}))
        with pytest.raises(HTTPException):
            service.shared_view(db, b.id, house['id'], a.id, 'networth', resource='property')
        ticket = service.request_export(db, b.id, house['id'], a.id, 'networth', resource='property')
        assert len(service.fetch_export(db, b.id, ticket['id'])['data']['observations']) == 1
        service.grant(db, a.id, house['id'], grant.model_copy(update={'expected_revision': 2, 'granted': False}))
        with pytest.raises(HTTPException):
            service.fetch_export(db, b.id, ticket['id'])


def test_resource_migration_roundtrip(db_engine):
    from alembic import command
    from backend.core.migrations_runner import _alembic_cfg
    from backend.core.owned_stores import validate_coverage
    cfg = _alembic_cfg(str(db_engine.url))
    command.downgrade(cfg, '0173')
    command.upgrade(cfg, 'head')
    validate_coverage()
from tests.test_stage_c_statements import synthetic_config


def test_unverified_adult_declarations(db_engine):
    from backend.models.models import Household, HouseholdMembership
    from backend.schemas.household import HouseholdCreate
    with Session(db_engine) as db:
        a, b, _, house, invite, _ = sharing(db)
        for row in (db.get(Household, house['id']), db.get(HouseholdMembership, invite['id'])):
            assert row.adult_assurance == 'unverified'
            assert row.adult_statement_version == service.ADULT_STATEMENT_VERSION
            assert row.adult_declared_at is not None
        with pytest.raises(ValueError):
            HouseholdCreate(label='x', adult_confirmed=True, identity_document='forbidden')


def test_exact_ownership_seeded():
    from fractions import Fraction
    import random
    rng = random.Random(206)
    assert service.allocate_paise(1, {'b': Fraction(1, 2), 'a': Fraction(1, 2)})['allocations'] == {'b': 0, 'a': 1}
    for _ in range(2500):
        denominator = rng.randint(1, 1000000)
        remaining = denominator
        shares = {}
        for i in range(rng.randint(1, 12)):
            value = rng.randint(0, remaining)
            remaining -= value
            shares[str(i)] = Fraction(value, denominator)
        total = rng.randint(0, 10**12)
        result = service.allocate_paise(total, shares)
        assert sum(result['allocations'].values()) + result['unallocated_paise'] == total
        assert result == service.allocate_paise(total, dict(reversed(list(shares.items()))))
        for key, share in shares.items():
            assert abs(result['allocations'][key] - total * share) < 1
    with pytest.raises(ValueError):
        service.allocate_paise(10, {'a': Fraction(3, 4), 'b': Fraction(1, 2)})
    with pytest.raises(ValueError):
        service.allocate_paise(10, {'a': 0.5})
    item = observation(value=1)
    item.pop('share_bps')
    item['share_percent'] = '33.333333333333333333'
    payload = book([item])
    result = service.consolidate([payload.data.model_dump(mode='json')])['observations'][0]
    assert result['allocated_paise'] + result['unallocated_paise'] == 1
    assert result['unallocated_share'] != '0'
