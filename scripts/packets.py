"""Validation and size controls for Codex Debate packets."""

from __future__ import annotations

import json
from typing import Any, Mapping


class PacketValidationError(ValueError):
    """Raised when a packet violates the runtime contract."""


DEFAULT_LIMITS = {
    "max_packet_chars": 24000,
    "max_context_item_chars": 6000,
    "max_context_items": 8,
    "max_evidence_items": 12,
    "max_result_chars": 12000,
    "max_artifacts": 12,
}


def _require_mapping(packet: Mapping[str, Any], name: str) -> None:
    if not isinstance(packet, Mapping):
        raise PacketValidationError(f"{name} must be an object")
    if packet.get("packet_version") != 1:
        raise PacketValidationError(f"{name} must use packet_version 1")


def _require_fields(packet: Mapping[str, Any], fields: tuple[str, ...], name: str) -> None:
    missing = [field for field in fields if field not in packet]
    if missing:
        raise PacketValidationError(f"{name} missing fields: {', '.join(missing)}")


def _check_list(value: Any, field: str, limit: int) -> None:
    if not isinstance(value, list):
        raise PacketValidationError(f"{field} must be a list")
    if len(value) > limit:
        raise PacketValidationError(f"{field} exceeds limit {limit}")


def _check_strings(items: list[Any], field: str, item_limit: int) -> None:
    for item in items:
        if not isinstance(item, str):
            raise PacketValidationError(f"{field} items must be strings")
        if len(item) > item_limit:
            raise PacketValidationError(f"{field} item exceeds limit {item_limit}")


def _check_size(packet: Mapping[str, Any], name: str, limits: Mapping[str, int]) -> None:
    try:
        serialized = json.dumps(packet, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise PacketValidationError(f"{name} is not JSON serializable") from exc
    if len(serialized) > limits["max_packet_chars"]:
        raise PacketValidationError(f"{name} exceeds packet limit {limits['max_packet_chars']}")


def validate_task_packet(packet: Mapping[str, Any], limits: Mapping[str, int] | None = None) -> dict[str, Any]:
    limits = limits or DEFAULT_LIMITS
    _require_mapping(packet, "task packet")
    _require_fields(
        packet,
        (
            "packet_version",
            "task_id",
            "role",
            "objective",
            "relevant_context",
            "constraints",
            "evidence",
            "artifacts",
            "required_output",
            "acceptance_criteria",
            "privacy",
        ),
        "task packet",
    )
    if not isinstance(packet["objective"], str) or not packet["objective"].strip():
        raise PacketValidationError("task packet objective must be a non-empty string")
    _check_list(packet["relevant_context"], "relevant_context", limits["max_context_items"])
    _check_strings(packet["relevant_context"], "context item", limits["max_context_item_chars"])
    _check_list(packet["evidence"], "evidence", limits["max_evidence_items"])
    _check_list(packet["artifacts"], "artifacts", limits["max_artifacts"])
    _check_list(packet["acceptance_criteria"], "acceptance_criteria", limits["max_context_items"])
    _check_size(packet, "task packet", limits)
    return dict(packet)


def validate_result_packet(packet: Mapping[str, Any], limits: Mapping[str, int] | None = None) -> dict[str, Any]:
    limits = limits or DEFAULT_LIMITS
    _require_mapping(packet, "result packet")
    _require_fields(
        packet,
        (
            "packet_version",
            "task_id",
            "expert_id",
            "status",
            "result",
            "key_evidence",
            "disagreements",
            "risks",
            "confidence",
            "validation",
            "degraded",
        ),
        "result packet",
    )
    if "raw_transcript" in packet:
        raise PacketValidationError("raw_transcript must not be forwarded in a result packet")
    if packet["status"] not in {"success", "failed", "partial"}:
        raise PacketValidationError("result packet status is invalid")
    if not isinstance(packet["confidence"], (int, float)) or not 0 <= packet["confidence"] <= 1:
        raise PacketValidationError("result packet confidence must be between 0 and 1")
    for field in ("key_evidence", "disagreements", "risks", "validation"):
        _check_list(packet[field], field, limits["max_evidence_items"])
        _check_strings(packet[field], field, limits["max_context_item_chars"])
    result_text = json.dumps(packet["result"], ensure_ascii=False)
    if len(result_text) > limits["max_result_chars"]:
        raise PacketValidationError("result exceeds result limit")
    _check_size(packet, "result packet", limits)
    return dict(packet)


def validate_discovery_result(result: Mapping[str, Any], limits: Mapping[str, int] | None = None) -> dict[str, Any]:
    limits = limits or DEFAULT_LIMITS
    _require_mapping(result, "discovery result")
    _require_fields(result, ("packet_version", "capability_id", "candidates"), "discovery result")
    _check_list(result["candidates"], "candidates", 30)
    for candidate in result["candidates"]:
        if not isinstance(candidate, Mapping):
            raise PacketValidationError("discovery candidates must be objects")
        for field in ("model_id", "label", "capabilities", "evidence", "access_claims"):
            if field not in candidate:
                raise PacketValidationError(f"candidate missing field: {field}")
        _check_list(candidate["evidence"], "candidate evidence", limits["max_evidence_items"])
    _check_size(result, "discovery result", limits)
    return dict(result)


def validate_browser_observation(observation: Mapping[str, Any]) -> dict[str, Any]:
    _require_mapping(observation, "browser observation")
    _require_fields(
        observation,
        ("packet_version", "provider_id", "state", "page_url", "answer", "signals"),
        "browser observation",
    )
    valid_states = {
        "READY",
        "AUTH_REQUIRED",
        "RATE_LIMITED",
        "MODEL_UNAVAILABLE",
        "SITE_ERROR",
        "AUTOMATION_BLOCKED",
        "UNKNOWN_FAILURE",
    }
    if observation["state"] not in valid_states:
        raise PacketValidationError("browser observation state is invalid")
    if not isinstance(observation["signals"], list):
        raise PacketValidationError("browser observation signals must be a list")
    _check_size(observation, "browser observation", DEFAULT_LIMITS)
    return dict(observation)
