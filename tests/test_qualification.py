import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import qualification
import registry


class QualificationTests(unittest.TestCase):
    def test_fresh_qualification_is_reused_for_same_expert_and_task_class(self):
        record = qualification.make_record(
            "expert-1", "coding", 0.8, ["test-1"], datetime.now(timezone.utc)
        )

        self.assertTrue(qualification.is_fresh(record, now=datetime.now(timezone.utc)))

    def test_qualification_score_is_bounded(self):
        record = qualification.make_record(
            "expert-1", "coding", 1.5, ["test-1"], datetime.now(timezone.utc)
        )

        self.assertEqual(record["score"], 1.0)

    def test_qualification_can_be_stored_on_registered_expert(self):
        state = registry.empty_registry()
        registry.add_model(state, {"model_id": "model-1", "capabilities": ["coding"]})
        registry.add_provider(state, {"provider_id": "provider-1", "transport": "codex_native", "model_refs": ["model-1"]})
        registry.add_expert(
            state,
            {
                "expert_id": "expert-1",
                "model_ref": "model-1",
                "provider_ref": "provider-1",
                "capabilities": ["coding"],
            },
        )
        record = qualification.make_record(
            "expert-1", "coding", 0.8, ["test-1"], datetime.now(timezone.utc), "coding"
        )

        qualification.store_record(state, record)

        self.assertEqual(state["experts"]["expert-1"]["qualification"]["score"], 0.8)
