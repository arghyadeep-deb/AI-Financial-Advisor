"""Source precedence for financial facts (T114, architecture.md > source precedence).

Rule ``precedence.v1``: a fact is taken from the most authoritative available
source.  Two sources for the SAME fact and period are never summed; if they
disagree beyond a tolerance the result is flagged ``conflict`` and the
higher-precedence value is used until the user resolves it.  Until feature 002
adds ledger/statement sources, only ``user_declared`` and the projection
labels exist, but the contract is fixed here so consumers do not fork.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional

RULE_VERSION = "precedence.v1"

# Highest authority first.  "projected" and "estimated" are never facts.
ORDER = ("verified_statement", "ledger", "user_confirmed", "user_declared", "derived_estimate", "projected")
NON_FACT = {"projected", "derived_estimate"}
CONFLICT_TOLERANCE_PAISE = 100  # Rs 1


@dataclass(frozen=True)
class Candidate:
    source: str
    value_paise: Optional[int]


@dataclass(frozen=True)
class Resolved:
    value_paise: Optional[int]
    source: Optional[str]
    conflict: bool
    is_fact: bool
    rule_version: str = RULE_VERSION


def resolve(candidates: Iterable[Candidate]) -> Resolved:
    """Pick one value for a fact.  Never aggregates across sources."""
    usable = [c for c in candidates if c.value_paise is not None]
    unknown = [c.source for c in usable if c.source not in ORDER]
    if unknown:
        raise ValueError(f"unknown source(s): {unknown}")
    if not usable:
        return Resolved(None, None, False, False)
    usable.sort(key=lambda c: ORDER.index(c.source))
    best = usable[0]
    conflict = any(abs(c.value_paise - best.value_paise) > CONFLICT_TOLERANCE_PAISE
                   for c in usable[1:] if c.source not in NON_FACT)
    return Resolved(best.value_paise, best.source, conflict, best.source not in NON_FACT)


def resolve_all(by_fact: Dict[str, Iterable[Candidate]]) -> Dict[str, Resolved]:
    return {k: resolve(v) for k, v in by_fact.items()}
