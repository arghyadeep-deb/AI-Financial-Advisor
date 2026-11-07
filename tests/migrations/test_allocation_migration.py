from alembic import command
import pytest
from sqlalchemy import create_engine, inspect, text

from backend.core.migrations_runner import _alembic_cfg
from backend.models.models import AllocationPlan


def test_allocation_upgrade_downgrade_recovery(tmp_path):
    url = f"sqlite:///{(tmp_path / 'allocation.db').as_posix()}"
    cfg = _alembic_cfg(url)
    command.upgrade(cfg, "0003")
    command.upgrade(cfg, "0050")
    eng = create_engine(url)
    assert {c["name"] for c in inspect(eng).get_columns("allocation_plans")} == set(AllocationPlan.__table__.columns.keys())
    command.downgrade(cfg, "0003")
    assert "allocation_plans" not in inspect(eng).get_table_names()
    command.upgrade(cfg, "0050")
    with eng.begin() as c:
        c.execute(text("INSERT INTO users (id,email,full_name,hashed_password) VALUES (1,'test@e.test','T','disabled')"))
        c.execute(text("INSERT INTO allocation_plans VALUES ('p',1,1,1,'{}','{}',CURRENT_TIMESTAMP)"))
    with pytest.raises(RuntimeError, match="evidence exists"):
        command.downgrade(cfg, "0003")
    with eng.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM allocation_plans")).scalar_one() == 1
    eng.dispose()
