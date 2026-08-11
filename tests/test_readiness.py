import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import registry


class ReadinessTests(unittest.TestCase):
    def test_readiness_updates_provider_and_matching_experts(self):
        state = registry.empty_registry()
        registry.add_model(state, {"model_id": "model-1", "capabilities": ["coding"]})
        registry.add_provider(state, {"provider_id": "provider-1", "transport": "browser", "model_refs": ["model-1"]})
        registry.add_expert(
            state,
            {
                "expert_id": "expert-1",
                "model_ref": "model-1",
                "provider_ref": "provider-1",
                "capabilities": ["coding"],
            },
        )

        registry.update_readiness(state, "provider-1", "READY")

        self.assertEqual(state["providers"]["provider-1"]["status"], "ready")
        self.assertEqual(state["experts"]["expert-1"]["status"], "ready")

    def test_non_ready_state_does_not_look_like_authentication(self):
        state = registry.empty_registry()
        registry.add_model(state, {"model_id": "model-1", "capabilities": ["coding"]})
        registry.add_provider(state, {"provider_id": "provider-1", "transport": "browser", "model_refs": ["model-1"]})

        registry.update_readiness(state, "provider-1", "RATE_LIMITED")

        self.assertEqual(state["providers"]["provider-1"]["readiness_state"], "RATE_LIMITED")
        self.assertNotEqual(state["providers"]["provider-1"]["readiness_state"], "AUTH_REQUIRED")
