"""Safe migration runner (T103).

Handles three situations:

1. Empty database           -> run all migrations.
2. Legacy database with the 818b219 tables but no ``alembic_version``
   (e.g. the shipped ``advisor.db``) -> back up (SQLite file copy; for
   PostgreSQL the operator must have taken a ``pg_dump``), report dry-run
   counts, stamp ``0001`` and upgrade.  Existing rows are preserved.
3. Versioned database       -> upgrade to head.

CLI:  python -m backend.core.migrations_runner {status|dry-run|upgrade|downgrade REV}
"""
from __future__ import annotations

import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from alembic import command
from alembic.config import Config as AlembicConfig
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, pool, text

ROOT = Path(__file__).resolve().parent.parent.parent
BASELINE_REVISION = "0001"
LEGACY_TABLES = {"users", "financial_profiles", "financial_state", "threads", "messages"}


def _alembic_cfg(url: str) -> AlembicConfig:
    cfg = AlembicConfig(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return cfg


def _engine(url: str):
    return create_engine(url, poolclass=pool.NullPool)


def current_state(url: str) -> Dict[str, Any]:
    cfg = _alembic_cfg(url)
    head = ScriptDirectory.from_config(cfg).get_current_head()
    eng = _engine(url)
    try:
        with eng.connect() as conn:
            tables = set(inspect(conn).get_table_names())
            current = MigrationContext.configure(conn).get_current_revision()
    finally:
        eng.dispose()
    if current is None and LEGACY_TABLES <= tables:
        status = "legacy_unversioned"
    elif current is None:
        status = "empty"
    elif current != head:
        status = "behind"
    else:
        status = "current"
    return {"status": status, "current": current, "head": head, "at_head": current == head and head is not None,
            "tables": sorted(tables)}


def row_counts(url: str) -> Dict[str, int]:
    eng = _engine(url)
    out: Dict[str, int] = {}
    try:
        with eng.connect() as conn:
            for t in sorted(LEGACY_TABLES & set(inspect(conn).get_table_names())):
                out[t] = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar_one()
    finally:
        eng.dispose()
    return out


def backup_sqlite(url: str, backup_dir: Optional[Path] = None) -> Optional[Path]:
    if not url.startswith("sqlite"):
        return None
    path_part = url.split("///", 1)[1]
    src = Path(path_part)
    if not src.is_absolute():
        src = Path.cwd() / src
    if not src.exists():
        return None
    backup_dir = Path(backup_dir) if backup_dir else src.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = backup_dir / f"{src.stem}-pre-migration-{stamp}{src.suffix}"
    shutil.copy2(src, dest)
    return dest


def migrate(url: str, *, backup_dir: Optional[Path] = None, target: str = "head",
            backup_confirmed: bool = False) -> Dict[str, Any]:
    """Bring ``url`` to ``target``.  Returns a report (counts before/after, backup path)."""
    state = current_state(url)
    report: Dict[str, Any] = {"before": state, "backup": None, "counts_before": {}, "counts_after": {}}
    cfg = _alembic_cfg(url)

    if state["status"] == "legacy_unversioned":
        report["counts_before"] = row_counts(url)
        backup = backup_sqlite(url, backup_dir)
        report["backup"] = str(backup) if backup else None
        if not url.startswith("sqlite") and not backup_confirmed:
            raise RuntimeError(
                "Legacy PostgreSQL database detected. Take a pg_dump backup, then re-run "
                "with backup_confirmed=True (CLI: upgrade --i-have-a-backup)."
            )
        command.stamp(cfg, BASELINE_REVISION)
    elif state["status"] in ("behind", "current"):
        report["counts_before"] = row_counts(url)

    command.upgrade(cfg, target)
    report["after"] = current_state(url)
    report["counts_after"] = row_counts(url)
    return report


def main(argv=None) -> int:  # pragma: no cover - thin CLI
    from backend.core.config import config as app_config
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0] if argv else "status"
    url = app_config.DATABASE_URL
    if cmd == "status":
        print(current_state(url))
    elif cmd == "dry-run":
        print({"state": current_state(url), "row_counts": row_counts(url),
               "note": "dry run: nothing changed; upgrade will back up SQLite first"})
    elif cmd == "upgrade":
        print(migrate(url, backup_confirmed="--i-have-a-backup" in argv))
    elif cmd == "downgrade":
        command.downgrade(_alembic_cfg(url), argv[1])
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
