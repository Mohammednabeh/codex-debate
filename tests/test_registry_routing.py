import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import registry
import routing


class RegistryRoutingTests(unittest.TestCase):
    def test_fresh_ready_expert_is_selected_without_degradation(self):
        state = registry.empty_registry()
        now = datetime.now(timezone.utc)
        registry.add_capability(state, {"capability_id": "coding", "freshness_days": 7})
        registry.add_model(state, {"model_id": "model-1", "capabilities": ["coding"]})
        registry.add_provider(state, {"provider_id": "provider-1", "transport": "codex_native", "model_refs": ["model-1"]})
        registry.add_expert(
            state,
            {
                "expert_id": "expert-1",
                "model_ref": "model-1",
                "provider_ref": "provider-1",
                "capabilities": ["coding"],
                "qualification": {"score": 0.9, "tested_at": now.isoformat(), "task_class": "coding"},
                "reliability": 0.8,
                "status": "ready",
                "last_readiness_check": now.isoformat(),
            },
        )

        decision = routing.choose_route("coding", state, now=now)

        self.assertEqual(decision["primary_expert"], "expert-1")
        self.assertFalse(decision["degraded"])
        self.assertIn("qualification", decision["reason"])

    def test_stale_expert_is_not_selected_as_ready(self):
        state = registry.empty_registry()
        now = datetime.now(timezone.utc)
        registry.add_capability(state, {"capability_id": "coding", "freshness_days": 7})
        registry.add_model(state, {"model_id": "model-old", "capabilities": ["coding"]})
        registry.add_provider(state, {"provider_id": "provider-old", "transport": "codex_native", "model_refs": ["model-old"]})
        registry.add_expert(
            state,
            {
                "expert_id": "expert-old",
                "model_ref": "model-old",
                "provider_ref": "provider-old",
                "capabilities": ["coding"],
                "qualification": {"score": 1.0, "tested_at": (now - timedelta(days=8)).isoformat()},
                "reliability": 0.9,
                "status": "ready",
                "last_readiness_check": (now - timedelta(days=2)).isoformat(),
            },
        )

        decision = routing.choose_route("coding", state, now=now)

        self.assertTrue(decision["degraded"])
        self.assertEqual(decision["primary_expert"], "current_controller")
        self.assertIn("stale", decision["reason"])
