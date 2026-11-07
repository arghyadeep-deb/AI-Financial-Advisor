"""Deterministic post-agent guard (T105 / T106; FR-001, FR-004, FR-005, FR-007).

Agents and models propose; this module decides what is published.  It

* overwrites every canonical number (surplus, shortfall, contribution,
  emergency gap, score) with the values from the shared ``FinanceSnapshot``;
* caps the SIP plan at the affordable contribution and clears it when the
  contribution is zero/unavailable;
* removes income-band tax-saving figures and fund-switch/rebalance claims
  that would rest on holdings the user never supplied;
* suppresses named stocks/funds unless NAMED_PRODUCT_RECOMMENDATIONS is
  explicitly enabled (personalised securities recommendations are a gated
  capability, release-gates D05);
* records per-section provenance (llm | deterministic_fallback | deterministic
  | unavailable) and an overall status that cannot read as plain success when
  any section fell back or failed;
* rejects model narrative containing a rupee amount that is not traceable to
  deterministic outputs, or that claims a surplus during a deficit.
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from backend.core.money import format_inr, paise_to_float
from engines.cashflow import FinanceSnapshot

GUARD_VERSION = "guard.v1"

_AMOUNT = re.compile(
    r"(?:rs\.?|inr|₹)\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(lakhs?|lacs?|crores?|cr|k)?\b", re.I)
_SURPLUS_NEAR_AMOUNT = re.compile(
    r"surplus[^.\n]{0,40}(?:rs\.?|inr|₹)\s*[0-9]|(?:rs\.?|inr|₹)\s*[0-9][0-9,]*[^.\n]{0,40}surplus", re.I)
_SIP_AMOUNT = re.compile(
    r"\bsip\b[^.\n]{0,40}?(?:rs\.?|inr|₹)\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(lakhs?|lacs?|crores?|cr|k)?\b", re.I)
_FUND_SWITCH =re.compile(r"\b(switch|shift|move|redeem|sell)\b[^.\n]{0,60}\b(fund|funds|folio|scheme|holding)", re.I)
_TAXY = re.compile(r"\b(80C|80D|80CCD|tax|elss|nps)\b", re.I)
_NAMED = re.compile(
    r"\b(mirae|uti|hdfc|icici|sbi|axis|kotak|parag parikh|nippon|motilal|reliance|tcs|infosys|"
    r"bajaj|itc|wipro|adani|tata|larsen|maruti|zerodha|groww)\b", re.I)


def named_products_enabled() -> bool:
    return os.getenv("NAMED_PRODUCT_RECOMMENDATIONS", "false").strip().lower() == "true"


# ── helpers ────────────────────────────────────────────────────────────────

def _rupees(paise: Optional[int]) -> Optional[float]:
    return paise_to_float(paise)


def _numeric_leaves(obj: Any) -> Iterable[float]:
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        yield float(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _numeric_leaves(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _numeric_leaves(v)


def allowed_amounts(snapshot: FinanceSnapshot, deterministic_parts: List[Any],
                    agent_profile: Dict[str, Any]) -> Set[int]:
    vals: Set[float] = set()
    for part in deterministic_parts:
        vals.update(_numeric_leaves(part))
    vals.update(_numeric_leaves(agent_profile))
    for k, v in snapshot.to_dict().items():
        if k.endswith("_paise") and isinstance(v, int):
            vals.add(v / 100)
    out: Set[int] = set()
    for v in vals:
        for derived in (v, v / 12, v * 12):
            out.add(int(round(derived)))
    return out


def _amount_to_rupees(num: str, unit: Optional[str]) -> int:
    n = float(num.replace(",", ""))
    unit = (unit or "").lower()
    if unit.startswith(("lakh", "lac")):
        n *= 100_000
    elif unit.startswith(("crore", "cr")):
        n *= 10_000_000
    elif unit == "k":
        n *= 1_000
    return int(round(n))


def narrative_violation(text: Any, allowed: Set[int], snapshot: FinanceSnapshot,
                        check_amounts: bool = True) -> Optional[str]:
    """Return a reason code if model text must not be published, else None."""
    if not isinstance(text, str) or not text.strip():
        return None
    if snapshot.shortfall_paise > 0 and _SURPLUS_NEAR_AMOUNT.search(text):
        return "claims_surplus_during_deficit"
    for m in (_AMOUNT.finditer(text) if check_amounts else []):
        amt = _amount_to_rupees(m.group(1), m.group(2))
        if amt in (0, 1):
            continue
        if not any(abs(amt - a) <= 1 for a in allowed):
            return "unsupported_amount"
    if not named_products_enabled() and _NAMED.search(text):
        return "names_specific_product"
    avail = snapshot.available_contribution_paise
    if avail in (0, None) and (re.search(
            r"\b(start|begin|invest|increase)\b[^.\n]{0,40}\bsip\b[^.\n]{0,30}(?:rs\.?|₹)\s*[0-9]", text, re.I)
            or re.search(r"surplus[^.\n]{0,40}\b(to invest|investable)\b", text, re.I)):
        return "recommends_unaffordable_contribution"
    if avail:
        for m in _SIP_AMOUNT.finditer(text):
            if _amount_to_rupees(m.group(1), m.group(2)) * 100 > avail:
                return "sip_exceeds_affordable"
    return None


# ── section handling ───────────────────────────────────────────────────────

def _section_source(name: str, result: Dict[str, Any], errors: Dict[str, Any]) -> Tuple[str, str, Optional[str]]:
    """(status, source, reason) from the signals agents already emit."""
    if name in errors or (isinstance(result, dict) and result.get("error")):
        return "failed", "unavailable", "agent_error"
    if isinstance(result, dict) and (result.get("fallback_used") or result.get("parse_error")
                                     or result.get("llm_error")):
        return "degraded", "deterministic_fallback", "model_unavailable_or_invalid"
    return "complete", "llm", None


DETERMINISTIC_SECTIONS = {"health"}   # numbers come from the engine; text may still be model-written


def _generic_instrument(name: str, category: str) -> str:
    c = (category or "").lower()
    n = (name or "").lower()
    if "elss" in n or "tax" in c:
        return "Tax-saving equity fund (ELSS)"
    if "midcap" in n or "mid cap" in c:
        return "Mid-cap index fund"
    if "index" in n or "large cap" in c:
        return "Large-cap index fund"
    if "ppf" in n:
        return "Public Provident Fund (PPF)"
    if "liquid" in n or "liquid" in c:
        return "Liquid fund"
    if "nps" in n:
        return "National Pension System (NPS) Tier 1"
    if "gold" in n or "gold" in c:
        return "Gold (sovereign gold bond or gold fund)"
    return category or "Diversified fund"


def _guard_investment(inv: Dict[str, Any], snap: FinanceSnapshot, profile: Dict[str, Any]) -> Dict[str, Any]:
    avail_paise = snap.available_contribution_paise
    avail = int((avail_paise or 0) // 100)

    plan = [dict(p) for p in (inv.get("monthly_sip_plan") or []) if isinstance(p, dict)]
    if not named_products_enabled():
        for p in plan:
            p["instrument"] = _generic_instrument(p.get("instrument", ""), p.get("category", ""))
            p["rationale"] = re.sub(_NAMED, "", str(p.get("rationale", ""))).strip()
    total = sum(int(p.get("monthly_amount", 0) or 0) for p in plan)
    if avail <= 0:
        plan, total = [], 0
    elif total > avail:                                    # defence in depth; engine already caps
        scale = avail / total
        for p in plan:
            p["monthly_amount"] = int(p.get("monthly_amount", 0) * scale)
        plan = [p for p in plan if p["monthly_amount"] > 0]
        total = sum(p["monthly_amount"] for p in plan)

    inv["monthly_sip_plan"] = plan
    inv["total_monthly_investment"] = total
    inv["contribution"] = {
        "status": snap.contribution_status,
        "reason": snap.contribution_reason,
        "available_monthly_paise": avail_paise,
        "available_monthly": _rupees(avail_paise),
        "basis": "estimate_from_declared_profile",
    }
    inv["emergency_fund_status"] = {
        "current_months": round(snap.savings_paise / snap.expenses_paise, 1) if snap.expenses_paise else None,
        "target_months": 6,
        "gap_amount": _rupees(snap.emergency_gap_paise),
        "action": ("Build emergency fund first" if snap.emergency_gap_paise > 0
                   else "Emergency fund is adequate"),
    }
    # Income-band tax guesses are not published (FR-005).
    inv["tax_saving_plan"] = {
        "status": "unavailable",
        "reason": "Tax-saving estimates need your tax profile; income-band guesses were removed.",
        "total_tax_saved_annually": None,
    }
    if not named_products_enabled():
        inv["stock_recommendations"] = []
        inv["stock_strategy_note"] = ""
        inv["named_products"] = {"status": "gated",
                                 "reason": "Named stock and fund recommendations are disabled until suitability "
                                           "checks and product data are approved."}
    # lump sums may only come from savings above the emergency target
    max_lump = max(0, (snap.savings_paise - snap.emergency_target_paise) // 100)
    lump = [dict(x) for x in (inv.get("lumpsum_suggestions") or []) if isinstance(x, dict)]
    running = 0
    kept = []
    for x in lump:
        amt = int(x.get("amount", 0) or 0)
        if running + amt <= max_lump:
            if not named_products_enabled():
                x["instrument"] = _generic_instrument(x.get("instrument", ""), x.get("instrument", ""))
            kept.append(x)
            running += amt
    inv["lumpsum_suggestions"] = kept
    # projections are labelled, never observed balances (FR-004)
    for k in ("projected_corpus_5yr", "projected_corpus_10yr", "projected_corpus_20yr"):
        inv.setdefault(k, 0)
    inv["projection_label"] = "Illustrative projection, not a current balance or a guaranteed return."
    return inv


def _guard_health(h: Dict[str, Any], engine_result: Dict[str, Any], snap: FinanceSnapshot) -> Dict[str, Any]:
    for k in ("overall_score", "grade", "score_basis", "component_scores"):
        if k in engine_result:
            h[k] = engine_result[k]
    if "components" in engine_result:
        h["components"] = engine_result["components"]
    h["raw_metrics"] = engine_result.get("raw_metrics", {})
    h["monthly_surplus"] = _rupees(snap.surplus_paise)
    h["monthly_shortfall"] = _rupees(snap.shortfall_paise)
    if snap.shortfall_paise > 0:
        warns = [w for w in (h.get("detailed_warnings") or []) if isinstance(w, dict)]
        warns.insert(0, {
            "title": "Monthly Deficit",
            "severity": "critical",
            "summary": f"Expenses exceed income by {format_inr(snap.shortfall_paise)} every month.",
            "detail": ("Spending more than you earn drains savings or builds debt. Other suggestions that "
                       "need monthly cash (emergency-fund top-ups, SIPs) only apply once this gap is closed."),
            "impact": "Without a change the gap is paid from savings or borrowing.",
            "action_steps": ["Review your largest recurring expenses.",
                             "Identify what can be reduced or cancelled this month.",
                             "Look for ways to raise income."],
            "timeline": "Immediate",
        })
        h["detailed_warnings"] = warns
    return h


def _guard_rebalance(r: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "status": "unavailable",
        "reason": "Rebalancing needs your actual holdings by asset class. Only a total was provided, "
                  "so no drift or reallocation advice is shown.",
        "needs_rebalancing": False, "drift_analysis": [], "rebalancing_method": "none",
        "rebalancing_actions": [], "tax_impact": "", "next_rebalance_date": "",
        "summary": "Add your holdings by asset class to enable rebalancing.",
    }


def _guard_optimizer(o: Dict[str, Any], snap: FinanceSnapshot) -> Dict[str, Any]:
    keep = []
    for op in (o.get("optimization_opportunities") or []):
        blob = str(op)
        if _TAXY.search(blob):
            continue
        if not named_products_enabled() and _NAMED.search(blob):
            continue
        if snap.shortfall_paise > 0 and _FUND_SWITCH.search(blob):
            continue
        keep.append(op)
    o["optimization_opportunities"] = keep
    o["tax_saving_suggestions"] = []
    o["total_optimization_value"] = None
    o["tax_status"] = "unavailable"
    o["rebalancing_needed"] = False
    o["rebalancing_actions"] = []
    return o


def _guard_credit(c: Dict[str, Any], snap: FinanceSnapshot) -> Dict[str, Any]:
    c["credit_score_status"] = "known" if snap.credit_score is not None else "unknown"
    return c


def _guard_simulation(s: Dict[str, Any]) -> Dict[str, Any]:
    s["kind"] = "projection"
    s["projection_label"] = "Illustrative projections under stated assumptions; not balances or guarantees."
    return s


def deterministic_summary(snap: FinanceSnapshot, inv: Dict[str, Any], health: Dict[str, Any]) -> Dict[str, Any]:
    score = health.get("overall_score")
    grade = health.get("grade", "N/A")
    if snap.shortfall_paise > 0:
        flow = (f"Your monthly expenses exceed your income by {format_inr(snap.shortfall_paise)}. "
                "Closing that gap comes before any new investing.")
    elif snap.available_contribution_paise:
        flow = (f"You have an estimated {format_inr(snap.surplus_paise)} monthly surplus; "
                f"up to {format_inr(snap.available_contribution_paise)} a month looks available to invest "
                "after obligations and emergency-fund top-up.")
    elif snap.contribution_status == "unavailable":
        flow = snap.contribution_reason
    else:
        flow = "After your obligations and emergency-fund top-up there is nothing left to invest this month."
    score_txt = f"Your financial health score is {score}/100 ({grade})." if score is not None else ""
    priorities = []
    if snap.shortfall_paise > 0:
        priorities.append({"priority": 1, "action": f"Close the {format_inr(snap.shortfall_paise)} monthly gap "
                           "by reducing spending or raising income", "timeline": "immediate", "impact": "high"})
    if snap.emergency_gap_paise > 0 and snap.shortfall_paise == 0:
        priorities.append({"priority": len(priorities) + 1,
                           "action": f"Build your emergency fund: {format_inr(snap.emergency_gap_paise)} to go",
                           "timeline": "12 months", "impact": "high"})
    if snap.contribution_status == "unavailable":
        priorities.append({"priority": len(priorities) + 1,
                           "action": "Add your monthly debt payment so affordability can be calculated",
                           "timeline": "this week", "impact": "high"})
    return {
        "executive_summary": f"{score_txt} {flow}".strip(),
        "health_score": score, "grade": grade,
        "top_priorities": priorities[:3],
        "quick_wins": ["Review recurring subscriptions and fees this month"],
        "personalized_message": "These figures come from the profile you entered; update it any time to refresh them.",
        "narrative_source": "deterministic",
    }


def _guard_summary(s: Dict[str, Any], snap: FinanceSnapshot, results: Dict[str, Any],
                   allowed: Set[int], section_notes: Dict[str, Any]) -> Dict[str, Any]:
    health = results.get("health", {})
    inv = results.get("investment", {})
    reason = None
    texts: List[Any] = [s.get("executive_summary"), s.get("personalized_message")]
    texts += [p.get("action") if isinstance(p, dict) else p for p in (s.get("top_priorities") or [])]
    texts += list(s.get("quick_wins") or [])
    for t in texts:
        reason = reason or narrative_violation(t, allowed, snap)
    if s.get("fallback_used") or s.get("parse_error"):
        det = deterministic_summary(snap, inv, health)
        # fallback text from the agent is not trusted for amounts either
        reason = reason or None
        s.update({k: v for k, v in det.items() if k in ("executive_summary", "top_priorities", "quick_wins",
                                                        "personalized_message")})
        s["narrative_source"] = "deterministic_fallback"
    elif reason:
        det = deterministic_summary(snap, inv, health)
        s.update({k: v for k, v in det.items() if k in ("executive_summary", "top_priorities", "quick_wins",
                                                        "personalized_message")})
        s["narrative_source"] = "deterministic_after_rejection"
        s["narrative_rejected"] = reason
        section_notes["narrative_rejected"] = reason
    else:
        s["narrative_source"] = "model_validated"
    s["health_score"] = health.get("overall_score")
    s["grade"] = health.get("grade", "N/A")
    s["key_numbers"] = {
        "monthly_surplus": _rupees(snap.surplus_paise),
        "monthly_shortfall": _rupees(snap.shortfall_paise),
        "recommended_sip": inv.get("total_monthly_investment", 0),
        "emergency_fund_gap": _rupees(snap.emergency_gap_paise),
        "best_credit_card": (results.get("credit", {}).get("recommendations") or [{}])[0].get("card_name", "")
                            if results.get("credit") else "",
        "annual_tax_saving": None,
        "projected_corpus_10yr": inv.get("projected_corpus_10yr", 0),
    }
    return s


# ── public entry ───────────────────────────────────────────────────────────

def guard_allocation(canonical: Dict[str, Any], model_output: Any = None) -> Dict[str, Any]:
    """Allocation owns all facts. Model output has no publication authority.

    No free-text narrative is rendered until a separately evaluated structured
    explanation contract exists; arbitrary fields and named products are discarded.
    """
    from copy import deepcopy
    from backend.core.feature_flags import allocation_public_eligible
    result = deepcopy(canonical)
    result["narrative_status"] = "unavailable" if model_output is None else "rejected"
    result["public_eligible"] = allocation_public_eligible()
    result["named_products_eligible"] = named_products_enabled() and result["public_eligible"]
    return result


def enforce(results: Dict[str, Any], errors: Dict[str, Any], snapshot: FinanceSnapshot,
            agent_profile: Dict[str, Any], engine_health: Optional[Dict[str, Any]]
            ) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
    """Return (results, section_status, overall_status)."""
    results = {k: (dict(v) if isinstance(v, dict) else v) for k, v in results.items()}
    section_status: Dict[str, Any] = {}

    for name, res in results.items():
        status, source, reason = _section_source(name, res if isinstance(res, dict) else {}, errors)
        section_status[name] = {"status": status, "source": source, "reason": reason}

    if "health" in results and engine_health is not None and section_status["health"]["status"] != "failed":
        results["health"] = _guard_health(results["health"], engine_health, snapshot)
    elif "health" in results and engine_health is not None:
        # The engine is deterministic: a failed agent still yields engine numbers.
        results["health"] = _guard_health(results["health"], engine_health, snapshot)
        section_status["health"] = {"status": "degraded", "source": "deterministic", "reason": "agent_error"}

    if "investment" in results and section_status["investment"]["status"] != "failed":
        results["investment"] = _guard_investment(results["investment"], snapshot, agent_profile)
    elif "investment" in results:
        results["investment"] = _guard_investment({"monthly_sip_plan": []}, snapshot, agent_profile)
        section_status["investment"] = {"status": "degraded", "source": "deterministic", "reason": "agent_error"}
    if "rebalance" in results:
        results["rebalance"] = _guard_rebalance(results["rebalance"])
        section_status["rebalance"] = {"status": "complete", "source": "unavailable",
                                       "reason": "holdings_breakdown_not_provided"}
    if "optimizer" in results:
        results["optimizer"] = _guard_optimizer(results["optimizer"], snapshot)
    if "credit" in results:
        results["credit"] = _guard_credit(results["credit"], snapshot)
    if "simulation" in results:
        results["simulation"] = _guard_simulation(results["simulation"])

    if "summary" in results:
        det_parts = [results.get("health", {}), results.get("investment", {}), snapshot.to_dict()]
        allowed = allowed_amounts(snapshot, det_parts, agent_profile)
        notes: Dict[str, Any] = {}
        results["summary"] = _guard_summary(results["summary"], snapshot, results, allowed, notes)
        if notes:
            section_status["summary"]["narrative"] = notes
        if results["summary"].get("narrative_source", "").startswith("deterministic"):
            section_status["summary"]["status"] = "degraded"
            section_status["summary"]["source"] = "deterministic_fallback"

    statuses = [v["status"] for v in section_status.values()]
    if not statuses:
        overall = "failed"
    elif all(s == "failed" for s in statuses):
        overall = "failed"
    elif any(s == "failed" for s in statuses):
        overall = "partial"
    elif any(s == "degraded" for s in statuses):
        overall = "degraded"
    else:
        overall = "complete"
    return results, section_status, overall
