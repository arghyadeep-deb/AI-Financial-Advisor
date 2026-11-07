"""Metadata-only telemetry (T111 / FR-008; agent-quality.md > LangSmith payload contract).

* Local structured logging of ``{node, duration_ms, outcome, version}`` is
  always on and contains no inputs or outputs.
* LangSmith export is OFF unless TELEMETRY_EXPORT_ENABLED=true AND an API
  key is configured.  When on, inputs/outputs are replaced by an allow-list
  (process_inputs / process_outputs) and SDK-level hide flags are forced so
  automatic LangChain callbacks (parent, child, error, streaming) cannot
  carry prompts, profile data or model text.
* The application never depends on tracing: every failure here is swallowed.
"""
from __future__ import annotations

import functools
import logging
import os
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional

from backend.core.config import config

log = logging.getLogger("advisor.telemetry")

ALLOWED_META_KEYS = ("node", "duration_ms", "outcome", "error_type", "version", "retry_count")
TELEMETRY_VERSION = "meta.v1"

# Bounded in-memory ring buffer; used by tests and the local metrics view.
events: Deque[Dict[str, Any]] = deque(maxlen=500)


def export_enabled() -> bool:
    return bool(config.TRACING_ENABLED and os.getenv("LANGCHAIN_API_KEY"))


def configure_environment() -> None:
    """Called at import: never leaves raw tracing on by accident."""
    on = "true" if export_enabled() else "false"
    os.environ["LANGCHAIN_TRACING_V2"] = on
    os.environ["LANGSMITH_TRACING"] = on
    # Force payload hiding even when export is enabled (callbacks, children, errors).
    for flag in ("LANGSMITH_HIDE_INPUTS", "LANGSMITH_HIDE_OUTPUTS", "LANGSMITH_HIDE_METADATA",
                 "LANGCHAIN_HIDE_INPUTS", "LANGCHAIN_HIDE_OUTPUTS"):
        os.environ[flag] = "true"


def _record(node: str, duration_ms: float, outcome: str, error_type: Optional[str]) -> None:
    ev = {"node": node, "duration_ms": round(duration_ms, 1), "outcome": outcome, "version": TELEMETRY_VERSION}
    if error_type:
        ev["error_type"] = error_type
    events.append(ev)
    log.info("span node=%s outcome=%s duration_ms=%.1f", node, outcome, duration_ms)


def _only_allowed(meta: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in meta.items() if k in ALLOWED_META_KEYS}


def traceable(run_type: str = "chain", name: Optional[str] = None, tags: Optional[List[str]] = None) -> Callable:
    """Drop-in replacement for ``langsmith.traceable`` with allow-listed payloads."""

    def decorator(fn: Callable) -> Callable:
        node = name or fn.__name__
        exported: Dict[str, Callable] = {}

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            started = time.monotonic()
            outcome, err = "ok", None
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                outcome, err = "error", type(exc).__name__      # type only: messages may hold content
                raise
            finally:
                _record(node, (time.monotonic() - started) * 1000, outcome, err)

        if not hasattr(fn, "__call__"):
            return wrapper

        @functools.wraps(fn)
        def dispatch(*args, **kwargs):
            if export_enabled():
                try:
                    if "w" not in exported:
                        import langsmith
                        exported["w"] = langsmith.traceable(
                            run_type=run_type, name=node, tags=["metadata-only"],
                            process_inputs=lambda _inputs: {"node": node},
                            process_outputs=lambda _outputs: {"outcome": "ok"},
                        )(wrapper)
                    return exported["w"](*args, **kwargs)
                except ImportError:
                    pass
            return wrapper(*args, **kwargs)

        return dispatch

    return decorator


configure_environment()
