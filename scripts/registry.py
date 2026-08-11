"""Validated project registry for models, providers, experts, and capabilities."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
from urllib.parse import urlparse


TRANSPORTS = {"api", "local", "cli", "mcp", "codex_native", "browser"}
READINESS_STATES = {
    "READY",
    "AUTH_REQUIRED",
    "RATE_LIMITED",
    "MODEL_UNAVAILABLE",
    "SITE_ERROR",
    "AUTOMATION_BLOCKED",
    "UNKNOWN_FAILURE",
}
ENV_NAME = re.compile(r"^[A-Z_][A-Z0-9_]*$")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def empty_registry() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "models": {},
        "providers": {},
        "experts": {},
        "capabilities": {},
        "routing": {},
    }


def _timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def is_fresh(value: str | None, max_age_days: int, now: datetime | None = None) -> bool:
    checked = _timestamp(value)
    if checked is None:
        return False
    now = now or utc_now()
    return now - checked <= timedelta(days=max_age_days)


def add_capability(registry: dict[str, Any], record: Mapping[str, Any]) -> None:
    capability_id = str(record["capability_id"])
    registry["capabilities"][capability_id] = {
        "capability_id": capability_id,
        "task_classes": list(record.get("task_classes", [])),
        "priority": record.get("priority", "normal"),
        "privacy": record.get("privacy", "normal"),
        "escalation": int(record.get("escalation", 1)),
        "freshness_days": int(record.get("freshness_days", 7)),
        "primary_expert": record.get("primary_expert"),
        "fallback_experts": list(record.get("fallback_experts", [])),
    }


def add_model(registry: dict[str, Any], record: Mapping[str, Any]) -> None:
    model_id = str(record["model_id"])
    existing = registry["models"].get(model_id, {})
    registry["models"][model_id] = {
        "model_id": model_id,
        "label": record.get("label", model_id),
        "capabilities": sorted(set(existing.get("capabilities", [])) | set(record.get("capabilities", []))),
        "evidence": sorted(set(existing.get("evidence", [])) | set(record.get("evidence", []))),
        "limitations": sorted(set(existing.get("limitations", [])) | set(record.get("limitations", []))),
        "discovered_at": existing.get("discovered_at", record.get("discovered_at", utc_now().isoformat())),
        "availability_checked_at": record.get(
            "availability_checked_at", existing.get("availability_checked_at", utc_now().isoformat())
        ),
    }


def validate_provider_record(record: Mapping[str, Any]) -> None:
    provider_id = record.get("provider_id")
    if not isinstance(provider_id, str) or not provider_id.strip():
        raise ValueError("provider_id must be a non-empty string")
    transport = record.get("transport")
    if transport not in TRANSPORTS:
        raise ValueError(f"unsupported provider transport: {transport}")
    endpoint = record.get("endpoint")
    if endpoint is not None:
        parsed = urlparse(endpoint)
        if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password or not parsed.netloc:
            raise ValueError("endpoint must be an http(s) URL without embedded credentials")
        if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"} and not record.get(
            "allow_insecure_http", False
        ):
            raise ValueError("non-local API endpoints must use HTTPS")
    credential_env = record.get("credential_env")
    if credential_env is not None and not ENV_NAME.fullmatch(credential_env):
        raise ValueError("credential_env must be an environment variable name")
    if transport == "cli":
        command = record.get("command")
        if not isinstance(command, list) or not command or not all(isinstance(item, str) and item for item in command):
            raise ValueError("cli provider command must be a non-empty argument list")


def add_provider(registry: dict[str, Any], record: Mapping[str, Any]) -> None:
    validate_provider_record(record)
    provider_id = str(record["provider_id"])
    existing = registry["providers"].get(provider_id, {})
    model_refs = sorted(set(existing.get("model_refs", [])) | set(record.get("model_refs", [])))
    provider = dict(existing)
    provider.update(record)
    provider["model_refs"] = model_refs
    provider.setdefault("status", "configured")
    provider.setdefault("last_readiness_check", None)
    registry["providers"][provider_id] = provider


def add_expert(registry: dict[str, Any], record: Mapping[str, Any]) -> None:
    required = ("expert_id", "model_ref", "provider_ref", "capabilities")
    missing = [field for field in required if field not in record]
    if missing:
        raise ValueError(f"expert missing fields: {', '.join(missing)}")
    if record["model_ref"] not in registry["models"] and record["model_ref"] != "current_controller":
        raise ValueError("expert model_ref is not registered")
    if record["provider_ref"] not in registry["providers"] and record["provider_ref"] != "current_controller":
        raise ValueError("expert provider_ref is not registered")
    expert = dict(record)
    expert.setdefault("qualification", None)
    expert.setdefault("reliability", 0.5)
    expert.setdefault("status", "stale")
    expert.setdefault("last_readiness_check", None)
    registry["experts"][str(record["expert_id"])] = expert


def update_readiness(
    registry: dict[str, Any], provider_id: str, readiness_state: str, checked_at: str | None = None
) -> None:
    if readiness_state not in READINESS_STATES:
        raise ValueError(f"invalid readiness state: {readiness_state}")
    provider = registry["providers"].get(provider_id)
    if provider is None:
        raise ValueError(f"unknown provider: {provider_id}")
    checked_at = checked_at or utc_now().isoformat()
    provider["readiness_state"] = readiness_state
    provider["last_readiness_check"] = checked_at
    provider["status"] = "ready" if readiness_state == "READY" else "unavailable"
    for expert in registry["experts"].values():
        if expert.get("provider_ref") == provider_id:
            expert["last_readiness_check"] = checked_at
            expert["status"] = "ready" if readiness_state == "READY" else "blocked"
