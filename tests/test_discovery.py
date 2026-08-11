import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import discovery
import registry


class DiscoveryTests(unittest.TestCase):
    def test_discovery_request_requires_current_research_and_separate_access_claims(self):
        request = discovery.build_discovery_request("research", {"privacy": "normal"})

        self.assertEqual(request["action"], "research_current_experts")
        self.assertIn("access_claims", request["required_fields"])
        self.assertIn("current", request["instructions"])

    def test_discovery_result_registers_model_and_separate_provider(self):
        state = registry.empty_registry()
        result = {
            "packet_version": 1,
            "capability_id": "research",
            "candidates": [
                {
                    "model_id": "vendor/model-a",
                    "label": "Model A",
                    "capabilities": ["research"],
                    "evidence": ["https://example.com/model-a"],
                    "access_claims": [
                        {
                            "provider_id": "vendor-api",
                            "transport": "api",
                            "endpoint": "https://api.example.com/v1",
                            "credential_env": "VENDOR_API_KEY",
                        }
                    ],
                }
            ],
        }

        update = discovery.apply_discovery_result(state, result)

        self.assertEqual(update["models_added"], 1)
        self.assertIn("vendor/model-a", state["models"])
        self.assertIn("vendor-api", state["providers"])
        self.assertEqual(state["providers"]["vendor-api"]["model_refs"], ["vendor/model-a"])

    def test_discovery_deduplicates_same_model_and_preserves_sources(self):
        state = registry.empty_registry()
        result = {
            "packet_version": 1,
            "capability_id": "research",
            "candidates": [
                {
                    "model_id": "vendor/model-a",
                    "label": "Model A",
                    "capabilities": ["research"],
                    "evidence": ["https://example.com/one"],
                    "access_claims": [],
                },
                {
                    "model_id": "vendor/model-a",
                    "label": "Model A",
                    "capabilities": ["research", "analysis"],
                    "evidence": ["https://example.com/two"],
                    "access_claims": [],
                },
            ],
        }

        update = discovery.apply_discovery_result(state, result)

        self.assertEqual(update["models_added"], 1)
        self.assertEqual(set(state["models"]["vendor/model-a"]["capabilities"]), {"research", "analysis"})
        self.assertEqual(len(state["models"]["vendor/model-a"]["evidence"]), 2)
