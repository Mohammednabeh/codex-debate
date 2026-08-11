import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import packets


class PacketTests(unittest.TestCase):
    def test_task_packet_rejects_oversized_context_item(self):
        packet = {
            "packet_version": 1,
            "task_id": "task-1",
            "role": "coding",
            "objective": "Implement the change",
            "relevant_context": ["x" * (packets.DEFAULT_LIMITS["max_context_item_chars"] + 1)],
            "constraints": [],
            "evidence": [],
            "artifacts": [],
            "required_output": {"format": "markdown"},
            "acceptance_criteria": [],
            "privacy": "normal",
        }

        with self.assertRaisesRegex(packets.PacketValidationError, "context item"):
            packets.validate_task_packet(packet)


    def test_result_packet_does_not_forward_raw_transcript(self):
        raw = {
            "packet_version": 1,
            "task_id": "task-1",
            "expert_id": "expert-1",
            "status": "success",
            "result": {"answer": "done"},
            "key_evidence": ["evidence"],
            "disagreements": [],
            "risks": [],
            "confidence": 0.8,
            "validation": [],
            "degraded": False,
            "raw_transcript": "should not be accepted",
        }

        with self.assertRaisesRegex(packets.PacketValidationError, "raw_transcript"):
            packets.validate_result_packet(raw)
