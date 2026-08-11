"""Provider adapters and agent-mediated action handshakes."""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlparse

import packets


def _result(task_packet: dict[str, Any], expert_id: str, status: str, result: Any, risks=None) -> dict[str, Any]:
    return packets.validate_result_packet(
        {
            "packet_version": 1,
            "task_id": task_packet["task_id"],
            "expert_id": expert_id,
            "status": status,
            "result": result,
            "key_evidence": [],
            "disagreements": [],
            "risks": risks or [],
            "confidence": 0.0 if status == "failed" else 0.6,
            "validation": [],
            "degraded": False,
        }
    )


class ApiAdapter:
    def ask(self, provider: dict[str, Any], task_packet: dict[str, Any]) -> dict[str, Any]:
        packets.validate_task_packet(task_packet)
        endpoint = provider.get("endpoint")
        parsed = urlparse(endpoint or "")
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("API provider endpoint must be an http(s) URL")
        payload = json.dumps({"task_packet": task_packet}).encode("utf-8")
        request = urllib.request.Request(endpoint, data=payload, method="POST")
        request.add_header("Content-Type", "application/json")
        credential_env = provider.get("credential_env")
        if credential_env:
            token = os.environ.get(credential_env)
            if not token:
                return _result(task_packet, provider["provider_id"], "failed", {}, ["missing API credential"])
            request.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(request, timeout=int(provider.get("timeout_sec", 60))) as response:
                raw = response.read(120000)
            parsed_body = json.loads(raw.decode("utf-8"))
            return _result(task_packet, provider["provider_id"], "success", parsed_body)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            return _result(task_packet, provider["provider_id"], "failed", {}, [f"API request failed: {exc}"])


class CliAdapter:
    def ask(self, provider: dict[str, Any], task_packet: dict[str, Any]) -> dict[str, Any]:
        packets.validate_task_packet(task_packet)
        command = provider.get("command")
        if not isinstance(command, list) or not command or not all(isinstance(item, str) for item in command):
            raise ValueError("CLI provider command must be a non-empty argument list")
        env = os.environ.copy()
        for name in provider.get("env_passthrough", []):
            if name in os.environ:
                env[name] = os.environ[name]
        try:
            completed = subprocess.run(
                command,
                input=json.dumps({"task_packet": task_packet}),
                text=True,
                capture_output=True,
                timeout=int(provider.get("timeout_sec", 60)),
                shell=False,
                env=env,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return _result(task_packet, provider["provider_id"], "failed", {}, [f"CLI execution failed: {exc}"])
        if completed.returncode != 0:
            return _result(
                task_packet,
                provider["provider_id"],
                "failed",
                {},
                [f"CLI exited with status {completed.returncode}"],
            )
        try:
            body = json.loads(completed.stdout)
        except json.JSONDecodeError:
            body = {"text": completed.stdout[:12000]}
        return _result(task_packet, provider["provider_id"], "success", body)


def prepare_agent_action(provider: dict[str, Any], task_packet: dict[str, Any]) -> dict[str, Any]:
    packets.validate_task_packet(task_packet)
    return {
        "action": "agent_request",
        "provider_id": provider["provider_id"],
        "model_ref": provider.get("model_ref"),
        "task_packet": task_packet,
        "required_return": "ResultPacket v1 without raw_transcript",
    }


def prepare_browser_action(provider: dict[str, Any], task_packet: dict[str, Any]) -> dict[str, Any]:
    profile = provider.get("browser_profile") or {}
    provider_url = provider.get("endpoint") or profile.get("home_url")
    if not provider_url:
        raise ValueError("browser provider requires endpoint or browser_profile.home_url")
    return {
        "action": "browser_provider_task",
        "provider_id": provider["provider_id"],
        "provider_url": provider_url,
        "login_url": profile.get("login_url", provider_url),
        "browser_target": profile.get("browser_target", "browser_or_chrome"),
        "readiness_signals": profile.get("chat_ready_signals", []),
        "auth_required_signals": profile.get("auth_required_signals", []),
        "rate_limit_signals": profile.get("rate_limit_signals", []),
        "model_unavailable_signals": profile.get("model_unavailable_signals", []),
        "completion_signals": profile.get("completion_signals", []),
        "task_packet": task_packet,
        "instructions": "Return BrowserObservation v1. Never return credentials, cookies, or session tokens.",
    }


def consume_browser_observation(observation: dict[str, Any], task_packet: dict[str, Any]) -> dict[str, Any]:
    observation = packets.validate_browser_observation(observation)
    state = observation["state"]
    if state != "READY":
        return _result(task_packet, observation["provider_id"], "failed", {}, [state])
    return _result(task_packet, observation["provider_id"], "success", {"answer": observation["answer"]})
