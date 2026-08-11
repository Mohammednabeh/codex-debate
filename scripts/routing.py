"""Explainable rule-based expert routing and degraded fallback."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import registry


def choose_route(capability_id: str, state: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    now = now or registry.utc_now()
    capability = state.get("capabilities", {}).get(capability_id, {})
    freshness_days = int(capability.get("freshness_days", 7))
    eligible: list[tuple[tuple[float, float, float], dict[str, Any]]] = []
    stale_seen = False
    for expert in state.get("experts", {}).values():
        if capability_id not in expert.get("capabilities", []):
            continue
        if expert.get("status") != "ready":
            stale_seen = True
            continue
        if not registry.is_fresh(expert.get("last_readiness_check"), 1, now):
            stale_seen = True
            continue
        qualification = expert.get("qualification") or {}
        if not registry.is_fresh(qualification.get("tested_at"), freshness_days, now):
            stale_seen = True
            continue
        score = (
            float(qualification.get("score", 0.0)),
            float(expert.get("reliability", 0.0)),
            float(expert.get("last_readiness_check", "").replace("-", "").replace(":", "")[:8] or 0),
        )
        eligible.append((score, expert))
    eligible.sort(key=lambda item: item[0], reverse=True)
    if eligible:
        primary = eligible[0][1]
        fallbacks = [item[1]["expert_id"] for item in eligible[1:]]
        return {
            "capability": capability_id,
            "primary_expert": primary["expert_id"],
            "fallback_experts": fallbacks,
            "review_expert": fallbacks[0] if int(capability.get("escalation", 1)) >= 2 and fallbacks else None,
            "degraded": False,
            "reason": "selected READY expert by qualification, reliability, and readiness freshness",
        }
    reason = "no fresh READY expert available"
    if stale_seen:
        reason += "; registered candidates are stale or unavailable"
    return {
        "capability": capability_id,
        "primary_expert": "current_controller",
        "fallback_experts": [],
        "review_expert": None,
        "degraded": True,
        "reason": reason,
    }
