"""
Fenlara — Agent Selection Layer, V0.1 prototype

Pure function, no network, no DNS, no A2A/MCP, no registry, no LLM.

    select(offers, request) -> SelectionResult

Fenlara does not select agents. Fenlara selects execution offers.

    Fenlara = deterministic function
        offers + request
              |
           result

`agent_id` is identity/audit metadata only. No part of the constraint
or scoring logic ever branches on `agent_id` — every decision is made,
scored and reported per `offer_id`. This is deliberate: the same agent
may publish several competing offers (different price/latency/mode
tradeoffs for the same capability), and those offers must be able to
survive and be compared independently, exactly as if they came from
different agents.

Design contract:
  - constraints are HARD filters: an offer failing any constraint is
    rejected outright, never scored.
  - preferences are SOFT weights: only survivors are scored and compared.
  - a missing attribute needed for a constraint check is treated as a
    constraint FAILURE (fail-closed: "unknown" is not "acceptable").
  - a missing attribute needed for a scoring criterion is treated as the
    WORST possible score (0.0) for that criterion on that offer, and
    is reported in "warnings" rather than silently ignored.
  - preference weights are normalized to sum to 1; if they sum to 0,
    every survivor scores 0 and the tie-break rule alone decides.
  - ties are broken deterministically by offer_id (lexicographic),
    and reported explicitly rather than hidden.
  - this layer trusts the attributes it is given. It has no way to
    detect an offer publishing false values — that is the job of
    the discovery/registry layer upstream (see AINS's evidence model).
    A test below documents this boundary rather than papering over it.
  - staleness between selection and resolution (an offer going
    unavailable a second after being chosen) is also out of scope: the
    Resolution layer downstream is expected to re-verify before
    connecting, not this layer.
"""

from __future__ import annotations
from typing import Any


# Criteria where a LOWER raw value is BETTER (price, latency, ...).
# Everything not listed here is assumed HIGHER-is-better (trust, ...).
LOWER_IS_BETTER = {"price", "latency"}

FIELD_BY_CRITERION = {
    "trust": "trust",
    "price": "price",
    "latency": "latency_ms",
    "availability": "availability",
}


def _require_ids(offer: dict[str, Any]) -> tuple[str, str]:
    """Both offer_id and agent_id are REQUIRED (contract v0.1, Option A).

    agent_id is never read for constraint or scoring purposes, but it is
    not optional: every offer must be traceable to the agent that issued
    it, or Fenlara refuses to reason about it at all.
    """
    offer_id = offer.get("offer_id")
    if not offer_id:
        raise ValueError("every offer must carry a non-empty 'offer_id'")
    agent_id = offer.get("agent_id")
    if not agent_id:
        raise ValueError(f"offer '{offer_id}' is missing a required 'agent_id'")
    return offer_id, agent_id


def _constraint_reasons(offer: dict[str, Any], constraints: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    for key, limit in constraints.items():
        if key == "jurisdiction":
            value = offer.get("jurisdiction")
            if value is None:
                reasons.append("missing attribute: jurisdiction")
            elif value != limit:
                reasons.append(f"jurisdiction != {limit}")
        elif key == "max_price":
            value = offer.get("price")
            if value is None:
                reasons.append("missing attribute: price")
            elif value > limit:
                reasons.append(f"price > {limit}")
        elif key == "max_latency_ms":
            value = offer.get("latency_ms")
            if value is None:
                reasons.append("missing attribute: latency_ms")
            elif value > limit:
                reasons.append(f"latency_ms > {limit}")
        elif key == "required_protocol":
            value = offer.get("protocol")
            if value is None:
                reasons.append("missing attribute: protocol")
            elif value != limit:
                reasons.append(f"protocol != {limit}")
        else:
            # Unknown constraint key: fail closed rather than silently ignore it.
            reasons.append(f"unrecognized constraint: {key}")
    return reasons


def _normalize_weights(preferences: dict[str, float]) -> dict[str, float]:
    total = sum(preferences.values())
    if total <= 0:
        # No usable signal: everyone gets weight 0, the tie-break alone decides.
        return {k: 0.0 for k in preferences}
    return {k: v / total for k, v in preferences.items()}


def _criterion_score(offer: dict[str, Any], criterion: str,
                      pool: list[dict[str, Any]]) -> tuple[float, bool]:
    """Return (normalized_score in [0,1], was_missing)."""
    field = FIELD_BY_CRITERION.get(criterion, criterion)
    raw = offer.get(field)
    if raw is None:
        return 0.0, True

    values = [o.get(field) for o in pool if o.get(field) is not None]
    if not values:
        return 0.0, True
    lo, hi = min(values), max(values)
    if hi == lo:
        return 1.0, False  # everyone tied on this criterion -> full score for all

    if criterion in LOWER_IS_BETTER:
        return (hi - raw) / (hi - lo), False
    return (raw - lo) / (hi - lo), False


def select(offers: list[dict[str, Any]], request: dict[str, Any]) -> dict[str, Any]:
    constraints = request.get("constraints", {})
    preferences = _normalize_weights(request.get("preferences", {}))

    # Both ids are required and validated up front. agent_id is then never
    # read again below this point for any constraint or scoring purpose —
    # it is carried through purely to enrich the final "chosen" result.
    agent_by_offer: dict[str, Any] = {}
    for o in offers:
        offer_id, agent_id = _require_ids(o)
        agent_by_offer[offer_id] = agent_id

    rejections: dict[str, list[str]] = {}
    survivors: list[dict[str, Any]] = []
    for o in offers:
        reasons = _constraint_reasons(o, constraints)
        if reasons:
            rejections[o["offer_id"]] = reasons
        else:
            survivors.append(o)

    if not survivors:
        return {"chosen": None, "scores": {}, "rejections": rejections,
                "warnings": ["all offers rejected by hard constraints"]}

    scores: dict[str, dict[str, float]] = {}
    warnings: list[str] = []
    for o in survivors:
        offer_id = o["offer_id"]
        breakdown: dict[str, float] = {}
        total = 0.0
        for criterion, weight in preferences.items():
            score, missing = _criterion_score(o, criterion, survivors)
            if missing:
                warnings.append(f"{offer_id}: missing '{criterion}', scored 0")
            breakdown[criterion] = round(score, 4)
            total += weight * score
        breakdown["total"] = round(total, 4)
        scores[offer_id] = breakdown

    best_total = max(s["total"] for s in scores.values())
    winners = sorted(oid for oid, s in scores.items() if s["total"] == best_total)
    chosen_offer_id = winners[0]

    result = {
        "chosen": {"offer_id": chosen_offer_id, "agent_id": agent_by_offer[chosen_offer_id]},
        "scores": scores,
        "rejections": rejections,
        "warnings": warnings,
    }
    if len(winners) > 1:
        result["tie_with"] = winners[1:]
        warnings.append(f"tie between {winners}, resolved by offer_id order")
    return result