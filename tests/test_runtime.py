import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import debate
import registry
import storage


class RuntimeTests(unittest.TestCase):
    def test_vertical_slice_persists_and_resumes_session(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = Path(temp_dir)
            state = registry.empty_registry()
            now = datetime.now(timezone.utc).isoformat()
            registry.add_capability(state, {"capability_id": "coding", "freshness_days": 7})
            registry.add_model(state, {"model_id": "model-1", "capabilities": ["coding"]})
            registry.add_provider(
                state,
                {"provider_id": "provider-1", "transport": "codex_native", "model_refs": ["model-1"]},
            )
            registry.add_expert(
                state,
                {
                    "expert_id": "expert-1",
                    "model_ref": "model-1",
                    "provider_ref": "provider-1",
                    "capabilities": ["coding"],
                    "qualification": {"score": 0.9, "tested_at": now},
                    "reliability": 0.8,
                    "status": "ready",
                    "last_readiness_check": now,
                },
            )
            registry_path = state_dir / "registry.json"
            storage.write_json_atomic(registry_path, state)

            session, action = debate.start_session(state_dir, {"prompt": "Implement a parser"})
            self.assertEqual(action["action"], "capability_analysis")

            debate.accept_capability_analysis(
                state_dir,
                session["session_id"],
                {"capabilities": [{"capability_id": "coding", "priority": "high"}]},
            )
            route = debate.route_session(state_dir, session["session_id"])
            self.assertEqual(route["decisions"][0]["primary_expert"], "expert-1")
            self.assertFalse(route["decisions"][0]["degraded"])

            result = {
                "packet_version": 1,
                "task_id": route["tasks"][0]["task_id"],
                "expert_id": "expert-1",
                "status": "success",
                "result": {"answer": "implemented"},
                "key_evidence": [],
                "disagreements": [],
                "risks": [],
                "confidence": 0.8,
                "validation": [],
                "degraded": False,
            }
            completed = debate.submit_result(state_dir, session["session_id"], result)
            resumed = debate.resume_session(state_dir, session["session_id"])

            self.assertEqual(completed["status"], "completed")
            self.assertEqual(resumed["status"], "completed")
            self.assertEqual(resumed["results"][0]["result"]["answer"], "implemented")
