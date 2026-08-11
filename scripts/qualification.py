"""Small cached qualification records, not a benchmark framework."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


def make_record(
    expert_id: str,
    task_class: str,
    score: float,
    tests: list[str],
    tested_at: datetime,
    capability_id: str | None = None,
) -> dict[str, Any]:
    return {
        "expert_id": expert_id,
        "capability_id": capability_id,
        "task_class": task_class,
        "score": max(0.0, min(1.0, float(score))),
        "tests": list(tests[:3]),
        "tested_at": tested_at.astimezone(timezone.utc).isoformat(),
    }


def is_fresh(record: dict[str, Any], now: datetime | None = None, max_age_days: int = 30) -> bool:
    try:
        tested_at = datetime.fromisoformat(record["tested_at"].replace("Z", "+00:00"))
    except (KeyError, ValueError, TypeError):
        return False
    now = now or datetime.now(timezone.utc)
    return now - tested_at <= timedelta(days=max_age_days)


def store_record(state: dict[str, Any], record: dict[str, Any]) -> None:
    expert = state.get("experts", {}).get(record.get("expert_id"))
    if expert is None:
        raise ValueError("qualification expert is not registered")
    expert["qualification"] = dict(record)
    state.setdefault("evaluations", {})[record["expert_id"]] = dict(record)
