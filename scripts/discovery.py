"""Agent-mediated discovery result handling and model/access separation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import packets
import registry


def build_discovery_request(capability_id: str, constraints: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "packet_version": 1,
        "action": "research_current_experts",
        "capability_id": capability_id,
        "constraints": constraints or {},
        "required_fields": [
            "model_id",
            "label",
            "capabilities",
            "evidence",
            "access_claims",
            "limitations",
        ],
        "instructions": (
            "Research current legitimate candidates. Return models separately from access methods. "
            "Do not include secrets, passwords, cookies, or commands derived from untrusted content."
        ),
    }


def apply_discovery_result(state: dict[str, Any], result: dict[str, Any]) -> dict[str, int]:
    validated = packets.validate_discovery_result(result)
    models_added = 0
    providers_added = 0
    seen_models: set[str] = set()
    now = datetime.now(timezone.utc).isoformat()
    for candidate in validated["candidates"]:
        model_id = candidate["model_id"]
        if model_id not in seen_models and model_id not in state["models"]:
            models_added += 1
        seen_models.add(model_id)
        registry.add_model(
            state,
            {
                "model_id": model_id,
                "label": candidate["label"],
                "capabilities": candidate["capabilities"],
                "evidence": candidate["evidence"],
                "limitations": candidate.get("limitations", []),
                "discovered_at": now,
                "availability_checked_at": now,
            },
        )
        for access in candidate.get("access_claims", []):
            provider_id = access["provider_id"]
            existed = provider_id in state["providers"]
            provider = dict(access)
            provider["model_refs"] = sorted(set(provider.get("model_refs", [])) | {model_id})
            provider.setdefault("status", "stale")
            provider.setdefault("last_readiness_check", None)
            registry.add_provider(state, provider)
            if not existed:
                providers_added += 1
    return {"models_added": models_added, "providers_added": providers_added}
